import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, Tuple
from .minecraft_dqn import MinecraftDQN
from .minecraft_ppo import PPO
from .replay_buffer import ReplayBuffer

class MinecraftTrainer:
    """Trainer for the Minecraft RL agent"""
    
    def __init__(
        self,
        model,
        target_model=None,
        replay_buffer=None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        learning_rate: float = 1e-4,
        gamma: float = 0.99,
        target_update_freq: int = 1000,
        batch_size: int = 32,
        min_replay_size: int = 1000,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.1,
        epsilon_decay_steps: int = 10000,
        # PPO parameters
        lmbda: float = 0.95,
        eps: float = 0.2,
        actor_lr: float = 3e-4,
        critic_lr: float = 1e-3,
    ):
        """
        Args:
            model: Online model (DQN or PPO)
            target_model: Target model for DQN
            replay_buffer: Buffer for DQN
            device: Device to run the model on
            learning_rate: Learning rate for DQN optimizer
            gamma: Discount factor
            target_update_freq: How often to update target network for DQN
            batch_size: Size of training batches
            min_replay_size: Minimum size of replay buffer before training
            epsilon_start: Starting value of epsilon for ε-greedy exploration
            epsilon_end: Final value of epsilon
            epsilon_decay_steps: Number of steps to decay epsilon over
            lmbda: GAE parameter for PPO
            eps: PPO clip parameter
            actor_lr: Learning rate for PPO actor
            critic_lr: Learning rate for PPO critic
        """
        self.device = device
        self.model = model
        self.model_type = "DQN" if isinstance(model, MinecraftDQN) else "PPO"
        
        if self.model_type == "DQN":
            self.model = model.to(device)
            self.target_model = target_model.to(device)
            self.target_model.load_state_dict(self.model.state_dict())
            self.replay_buffer = replay_buffer
            self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
            self.gamma = gamma
            self.target_update_freq = target_update_freq
            self.batch_size = batch_size
            self.min_replay_size = min_replay_size
            self.epsilon_schedule = np.linspace(epsilon_start, epsilon_end, epsilon_decay_steps)
        else:  # PPO
            self.ppo = PPO(
                state_dim=model.state_dim,
                hidden_dim=model.hidden_dim,
                action_dim=model.action_dim,
                actor_lr=actor_lr,
                critic_lr=critic_lr,
                lmbda=lmbda,
                eps=eps,
                gamma=gamma,
                device=device
            )
        
        self.step_count = 0
        
    def get_epsilon(self) -> float:
        """Get current epsilon value for DQN"""
        if self.step_count < len(self.epsilon_schedule):
            return self.epsilon_schedule[self.step_count]
        return self.epsilon_schedule[-1]
    
    def select_action(self, obs: Dict[str, np.ndarray], training: bool = True) -> int:
        """
        Select an action using the appropriate policy
        
        Args:
            obs: Current observation
            training: Whether we're training (and should use exploration) or evaluating
            
        Returns:
            Selected action index
        """
        if self.model_type == "DQN":
            if training and np.random.random() < self.get_epsilon():
                # Random action
                return np.random.randint(self.model.action_value[-1].out_features)
            
            # Convert observation to tensors
            obs_tensors = {
                k: torch.from_numpy(v).unsqueeze(0).to(self.device)
                for k, v in obs.items()
            }
            
            with torch.no_grad():
                q_values = self.model(
                    obs_tensors["instruction"],
                    obs_tensors["state"],
                    obs_tensors["history"]
                )
                return q_values.argmax(dim=1).item()
        else:  # PPO
            # Convert observation to tensor
            obs_tensor = torch.cat([
                torch.from_numpy(obs["instruction"]),
                torch.from_numpy(obs["state"]),
                torch.from_numpy(obs["history"])
            ]).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                probs = self.ppo.actor(obs_tensor)
                if training:
                    action = torch.multinomial(probs, 1).item()
                else:
                    action = probs.argmax(dim=1).item()
                return action
    
    def train_step(self) -> float:
        """
        Perform one training step
        
        Returns:
            Loss value
        """
        if self.model_type == "DQN":
            if len(self.replay_buffer) < self.min_replay_size:
                return 0.0
                
            # Sample batch from replay buffer
            obs_batch, action_batch, reward_batch, next_obs_batch, done_batch = \
                self.replay_buffer.sample(self.batch_size)
                
            # Convert to tensors
            obs_tensors = {
                k: torch.from_numpy(v).to(self.device)
                for k, v in obs_batch.items()
            }
            
            next_obs_tensors = {
                k: torch.from_numpy(v).to(self.device)
                for k, v in next_obs_batch.items()
            }
            
            action_tensor = torch.from_numpy(action_batch).to(self.device)
            reward_tensor = torch.from_numpy(reward_batch).to(self.device)
            done_tensor = torch.from_numpy(done_batch).to(self.device)
            
            # Compute current Q values
            current_q_values = self.model(
                obs_tensors["instruction"],
                obs_tensors["state"],
                obs_tensors["history"]
            )
            current_q_values = current_q_values.gather(1, action_tensor.unsqueeze(1)).squeeze(1)
            
            # Compute target Q values
            with torch.no_grad():
                next_q_values = self.target_model(
                    next_obs_tensors["instruction"],
                    next_obs_tensors["state"],
                    next_obs_tensors["history"]
                )
                max_next_q_values = next_q_values.max(dim=1)[0]
                target_q_values = reward_tensor + (1 - done_tensor) * self.gamma * max_next_q_values
            
            # Compute loss and update
            loss = nn.MSELoss()(current_q_values, target_q_values)
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            # Update target network if needed
            self.step_count += 1
            if self.step_count % self.target_update_freq == 0:
                self.target_model.load_state_dict(self.model.state_dict())
                
            return loss.item()
        else:  # PPO
            # PPO training is handled by the PPO class
            return self.ppo.train_step()
    
    def save_model(self, path: str):
        """Save model to disk"""
        if self.model_type == "DQN":
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'target_model_state_dict': self.target_model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'step_count': self.step_count
            }, path)
        else:  # PPO
            self.ppo.save_model(path)
    
    def load_model(self, path: str):
        """Load model from disk"""
        if self.model_type == "DQN":
            checkpoint = torch.load(path)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.target_model.load_state_dict(checkpoint['target_model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.step_count = checkpoint['step_count']
        else:  # PPO
            self.ppo.load_model(path)
