import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple
from .rl_utils import compute_advantage
from .replay_buffer import ReplayBuffer
import random
import os
import pickle
import gzip
from .minecraft_rl_env import MinecraftRLEnv

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM

class Actor(nn.Module):
    def __init__(self, llm, tokenizer, hidden_dim: int, action_dim: int):
        super().__init__()
        self.llm = llm
        self.tokenizer = tokenizer
        hidden_state_dim = llm.config.hidden_size
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        self.fc = self.fc.to(llm.device)

    def forward(self, text: str) -> torch.Tensor:
        # Tokenize input text
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self.llm.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.llm(
                input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                output_hidden_states=True
            )
            hidden_states = outputs.hidden_states[-1].float()
        
        last_hidden = hidden_states[:, -1, :]
        action_probs = self.fc(last_hidden)
        return action_probs

class Critic(nn.Module):
    def __init__(self, llm, tokenizer, hidden_dim: int):
        super().__init__()
        self.llm = llm
        self.tokenizer = tokenizer
        hidden_state_dim = llm.config.hidden_size
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        self.fc = self.fc.to(llm.device)
    
    def forward(self, text: str) -> torch.Tensor:
        # Tokenize input text
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self.llm.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.llm(
                input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                output_hidden_states=True
            )
            hidden_states = outputs.hidden_states[-1].float()
        
        last_hidden = hidden_states[:, -1, :]
        value = self.fc(last_hidden)
        return value


def setup_models(model_name: str, hidden_dim: int = 256, action_dim: int = 6):
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    llm = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        device_map="cuda"
    )
    
    actor = Actor(
        llm=llm,
        tokenizer=tokenizer,
        hidden_dim=hidden_dim,
        action_dim=action_dim
    )
    
    critic = Critic(
        llm=llm,
        tokenizer=tokenizer,
        hidden_dim=hidden_dim
    )
    
    return tokenizer, actor, critic

class PPO:
    def __init__(
        self,
        hidden_dim: int,
        action_dim: int,
        actor_lr: float = 3e-4,
        critic_lr: float = 1e-3,
        gamma: float = 0.99,
        lmbda: float = 0.95,
        eps: float = 0.2,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        buffer_size: int = 10000,
        batch_size: int = 1,
    ):
        model_name = "/run/determined/NAS1/public/Qwen2.5-0.5B-Instruct-GPTQ-Int8"
        tokenizer, actor, critic = setup_models(model_name, hidden_dim, action_dim)
        self.actor = actor.to(device)
        self.critic = critic.to(device)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=actor_lr)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=critic_lr)
        
        self.gamma = gamma
        self.lmbda = lmbda
        self.eps = eps
        self.device = device

        self.batch_size = batch_size

        # Initialize replay buffer
        self.replay_buffer = ReplayBuffer(
            capacity=buffer_size,
        )
        if os.path.exists('rl_env/replay_buffer/replay_buffer.pkl.gz'):
            self.load_buffer('rl_env/replay_buffer/replay_buffer.pkl.gz')

        if os.path.exists('rl_env/ckpt/actor.pth') and os.path.exists('rl_env/ckpt/critic.pth'):
            self.load_ckpt('rl_env/ckpt/actor.pth', 'rl_env/ckpt/critic.pth')

    def save_ckpt(self, actor_path, critic_path):
        torch.save(self.actor.state_dict(), actor_path)
        torch.save(self.critic.state_dict(), critic_path)

    def load_ckpt(self, actor_path, critic_path):
        self.actor.load_state_dict(torch.load(actor_path))
        self.critic.load_state_dict(torch.load(critic_path))

    def load_buffer(self, buffer_path):
        # 读取压缩文件
        with gzip.open(buffer_path, 'rb') as f:
            buffer = pickle.load(f)
            self.replay_buffer.buffer = buffer

    def take_action(self, state, temperature=0.8):
        probs = self.actor(state)
        # 添加小值避免概率为0
        probs = probs + 1e-10
        # 温度缩放
        scaled_probs = (probs / temperature).softmax(dim=-1)
        # 可以添加噪声
        noise = torch.rand_like(scaled_probs) * 0.1
        noisy_probs = (scaled_probs + noise).softmax(dim=-1)
        action_dist = torch.distributions.Categorical(noisy_probs)
        action = action_dist.sample()
        return action.item()

        
    def train_step(self, idx=None):
        if len(self.replay_buffer.buffer) < self.batch_size:
            return
        # try:
        if idx == -1:
            batch = self.replay_buffer.buffer[-1]
        else:
            batch = random.sample(self.replay_buffer.buffer, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = states[0][0]
        next_states = next_states[0][0]

        # print('actions:', actions)
        # print('rewards:', rewards)
        # print('dones:', dones)
        # print('states:', states)

        # 直接将字符串输入传入模型
        actions = torch.tensor(actions, dtype=torch.int64).to(self.device)
        rewards = torch.tensor(rewards, dtype=torch.float).to(self.device)
        dones = torch.tensor(dones, dtype=torch.float).to(self.device)

        # Critic 现在接受字符串输入并返回值
        current_values = self.critic(states)
        next_values = self.critic(next_states)
        
        td_target = rewards + self.gamma * next_values * (1 - dones)
        td_delta = td_target - current_values
        advantage = compute_advantage(self.gamma, self.lmbda,
                                        td_delta.cpu()).to(self.device)

        # Actor 现在接受字符串输入并返回动作概率
        current_action_probs = self.actor(states)
        # print('current_action_probs:', current_action_probs.shape)
        # print('actions:', actions.shape)
        old_log_probs = torch.log(current_action_probs.gather(1, actions.unsqueeze(0))).detach()

        new_action_probs = self.actor(states)
        log_probs = torch.log(new_action_probs.gather(1, actions.unsqueeze(0)))
        
        ratio = torch.exp(log_probs - old_log_probs)
        surr1 = ratio * advantage
        surr2 = torch.clamp(ratio, 1 - self.eps,
                            1 + self.eps) * advantage  # 截断
        actor_loss = torch.mean(-torch.min(surr1, surr2))  # PPO损失函数
        critic_loss = torch.mean(
            F.mse_loss(current_values, td_target.detach()))
            
        self.actor_optimizer.zero_grad()
        self.critic_optimizer.zero_grad()
        actor_loss.backward()
        critic_loss.backward()
        self.actor_optimizer.step()
        self.critic_optimizer.step()
        
        print('actor_loss:', actor_loss.item(), 'critic_loss:', critic_loss.item())
            
        # except Exception as e:
        #     print(e)
        #     self.actor_optimizer.zero_grad()
        #     self.critic_optimizer.zero_grad()


    def update(self, transition_dict):
        states = transition_dict['states'],
        actions = transition_dict['actions']
        rewards = transition_dict['rewards']
        next_states = transition_dict['next_states']
        dones = transition_dict['dones']

        # Store transition in replay buffer
        self.replay_buffer.push(
            obs=states,
            action=actions,
            reward=rewards,
            next_obs=next_states,
            done=dones
        )



        # 保存压缩文件
        with gzip.open('rl_env/replay_buffer/replay_buffer.pkl.gz', 'wb') as f:
            pickle.dump(self.replay_buffer.buffer, f)

if __name__ == '__main__':

    rl_env = MinecraftRLEnv(
        max_instruction_length = 128,
        max_state_length = 256,
        max_history_length = 512,
    )

    rl_model = PPO(
        hidden_dim = 256,
        action_dim = rl_env.action_dim,
        actor_lr = 3e-4,
        critic_lr = 1e-3,
        gamma = 0.99,
        lmbda = 0.95,
        eps = 0.2,
        device = "cuda" if torch.cuda.is_available() else "cpu",
        buffer_size = 10000
    )

    # rl_model.train_step()
    # rl_model.train_step()
    rl_model.train_step(idx=-1)
    