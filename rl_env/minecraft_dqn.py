import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel
from typing import Dict, List, Tuple

class MinecraftDQN(nn.Module):
    """
    DQN network that processes text inputs and recommends Minecraft API actions.
    Uses a pre-trained transformer model to encode text inputs.
    """
    def __init__(
        self,
        num_actions: int,
        transformer_name: str = "gpt2",
        hidden_size: int = 768
    ):
        super(MinecraftDQN, self).__init__()
        
        # Load pre-trained transformer for text encoding
        self.text_encoder = AutoModel.from_pretrained(transformer_name)
        
        # Freeze transformer weights
        for param in self.text_encoder.parameters():
            param.requires_grad = False
            
        # Layers for processing encoded text
        self.instruction_proj = nn.Linear(self.text_encoder.config.hidden_size, hidden_size)
        self.state_proj = nn.Linear(self.text_encoder.config.hidden_size, hidden_size)
        self.history_proj = nn.Linear(self.text_encoder.config.hidden_size, hidden_size)
        
        # Attention mechanism to combine text features
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=8)
        
        # Action prediction layers
        self.action_value = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_actions)
        )
        
    def forward(
        self,
        instruction_tokens: torch.Tensor,
        state_tokens: torch.Tensor,
        history_tokens: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            instruction_tokens: Tokenized instruction text [batch_size, seq_len]
            state_tokens: Tokenized state text [batch_size, seq_len]
            history_tokens: Tokenized action history text [batch_size, seq_len]
            
        Returns:
            action_values: Q-values for each available API action
        """
        # Encode text inputs
        instruction_encoded = self.text_encoder(instruction_tokens)[0]  # [batch, seq, hidden]
        state_encoded = self.text_encoder(state_tokens)[0]
        history_encoded = self.text_encoder(history_tokens)[0]
        
        # Project to common hidden size
        instruction_proj = self.instruction_proj(instruction_encoded)
        state_proj = self.state_proj(state_encoded)
        history_proj = self.history_proj(history_encoded)
        
        # Combine features using attention
        combined_features = torch.cat([
            instruction_proj,
            state_proj,
            history_proj
        ], dim=1)  # [batch, 3*seq, hidden]
        
        # Self-attention over combined features
        attended_features, _ = self.attention(
            combined_features,
            combined_features,
            combined_features
        )
        
        # Pool features
        pooled_features = torch.mean(attended_features, dim=1)  # [batch, hidden]
        
        # Predict Q-values for each action
        action_values = self.action_value(pooled_features)
        
        return action_values
