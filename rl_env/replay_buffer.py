import numpy as np
from collections import deque
import random
from typing import Dict, List, Tuple

class ReplayBuffer:
    """Experience replay buffer for storing and sampling transitions"""
    
    def __init__(self, capacity: int = 10000):
        """
        Args:
            capacity: Maximum number of transitions to store in the buffer
        """
        self.buffer = deque(maxlen=capacity)
        
    def push(
        self,
        obs: Dict[str, np.ndarray],
        action: int,
        reward: float,
        next_obs: Dict[str, np.ndarray],
        done: bool
    ):
        """
        Store a transition in the buffer
        
        Args:
            obs: Current observation (instruction, state, history tokens)
            action: Action index that was taken
            reward: Reward that was received
            next_obs: Next observation
            done: Whether the episode ended
        """
        self.buffer.append((obs, action, reward, next_obs, done))
        
    def sample(self, batch_size: int) -> Tuple[Dict[str, np.ndarray], np.ndarray, np.ndarray, Dict[str, np.ndarray], np.ndarray]:
        """
        Sample a batch of transitions from the buffer
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            batch_obs: Batch of observations
            batch_actions: Batch of actions
            batch_rewards: Batch of rewards
            batch_next_obs: Batch of next observations
            batch_dones: Batch of done flags
        """
        transitions = random.sample(self.buffer, batch_size)
        
        # Separate transitions into batches
        batch_obs, batch_actions, batch_rewards, batch_next_obs, batch_dones = zip(*transitions)
        
        # Convert to numpy arrays
        batch_actions = np.array(batch_actions)
        batch_rewards = np.array(batch_rewards)
        batch_dones = np.array(batch_dones)
        
        # Combine observations into batches
        batch_obs_combined = {
            "instruction": np.stack([obs["instruction"] for obs in batch_obs]),
            "state": np.stack([obs["state"] for obs in batch_obs]),
            "history": np.stack([obs["history"] for obs in batch_obs])
        }
        
        batch_next_obs_combined = {
            "instruction": np.stack([obs["instruction"] for obs in batch_next_obs]),
            "state": np.stack([obs["state"] for obs in batch_next_obs]),
            "history": np.stack([obs["history"] for obs in batch_next_obs])
        }
        
        return batch_obs_combined, batch_actions, batch_rewards, batch_next_obs_combined, batch_dones
    
    def __len__(self) -> int:
        return len(self.buffer)
