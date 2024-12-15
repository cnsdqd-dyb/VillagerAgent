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

class Actor(nn.Module):
    def __init__(self, vocab_size: int, embedding_dim: int, hidden_dim: int, action_dim: int):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),  # *2 because bidirectional
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, seq_len)
        embedded = self.embedding(x)  # (batch_size, seq_len, embedding_dim)
        
        lengths = (x != 40478).sum(dim=1)

        # Pack padded sequence for LSTM
        packed = nn.utils.rnn.pack_padded_sequence(
            embedded, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        
        # Process with LSTM
        output, (hidden, _) = self.lstm(packed)
        
        # Concatenate forward and backward hidden states
        hidden_cat = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim=1)
        
        # Get action distribution
        action_probs = self.fc(hidden_cat)  # (batch_size, action_dim)
        return action_probs

class Critic(nn.Module):
    def __init__(self, vocab_size: int, embedding_dim: int, hidden_dim: int):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),  # *2 because bidirectional
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, seq_len)
        embedded = self.embedding(x)  # (batch_size, seq_len, embedding_dim)
        
        lengths = (x != 40478).sum(dim=1)

        # Pack padded sequence for LSTM
        packed = nn.utils.rnn.pack_padded_sequence(
            embedded, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        
        # Process with LSTM
        output, (hidden, _) = self.lstm(packed)
        
        # Concatenate forward and backward hidden states
        hidden_cat = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim=1)
        
        # Get value prediction
        value = self.fc(hidden_cat)  # (batch_size, 1)
        return value


class PPO:
    def __init__(
        self,
        vocab_size: int,
        state_dim: int,
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
        self.actor = Actor(vocab_size, state_dim, hidden_dim, action_dim).to(device)
        self.critic = Critic(vocab_size, state_dim, hidden_dim).to(device)
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

    def take_action(self, state):
        state = torch.tensor([state], dtype=torch.long).to(self.device)
        probs = self.actor(state)
        action_dist = torch.distributions.Categorical(probs)
        action = action_dist.sample()
        return action.item()
        
    def train_step(self):
        if len(self.replay_buffer.buffer) < self.batch_size:
            return
        try:
            batch = random.sample(self.replay_buffer.buffer, self.batch_size)
            states, actions, rewards, next_states, dones = zip(*batch)

            states = torch.tensor(states, dtype=torch.long).to(self.device).squeeze().unsqueeze(0)
            actions = torch.tensor(actions, dtype=torch.int64).to(self.device)
            rewards = torch.tensor(rewards, dtype=torch.float).to(self.device)
            next_states = torch.tensor(next_states, dtype=torch.long).to(self.device).squeeze().unsqueeze(0)
            dones = torch.tensor(dones, dtype=torch.float).to(self.device)

            td_target = rewards + self.gamma * self.critic(next_states) * (1 - dones)
            td_delta = td_target - self.critic(states)
            advantage = compute_advantage(self.gamma, self.lmbda,
                                               td_delta.cpu()).to(self.device)

            old_log_probs = torch.log(self.actor(states).gather(1, actions.unsqueeze(0))).detach()

            log_probs = torch.log(self.actor(states).gather(1, actions.unsqueeze(0)))
            ratio = torch.exp(log_probs - old_log_probs)
            surr1 = ratio * advantage
            surr2 = torch.clamp(ratio, 1 - self.eps,
                                1 + self.eps) * advantage  # 截断
            actor_loss = torch.mean(-torch.min(surr1, surr2))  # PPO损失函数
            critic_loss = torch.mean(
                F.mse_loss(self.critic(states), td_target.detach()))
            self.actor_optimizer.zero_grad()
            self.critic_optimizer.zero_grad()
            actor_loss.backward()
            critic_loss.backward()
            self.actor_optimizer.step()
            self.critic_optimizer.step()
            print('actor_loss:', actor_loss.item(), 'critic_loss:', critic_loss.item())
        except Exception as e:
            print(e)
            self.actor_optimizer.zero_grad()
            self.critic_optimizer.zero_grad()

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
        tokenizer_name = "openai-gpt",
        max_instruction_length = 128,
        max_state_length = 256,
        max_history_length = 512,
    )

    rl_model = PPO(
        vocab_size = rl_env.vocab_size,
        state_dim = rl_env.state_dim,
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

    rl_model.train_step()
    