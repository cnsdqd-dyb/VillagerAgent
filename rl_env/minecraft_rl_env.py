import gymnasium as gym
from gymnasium import spaces
import numpy as np
from transformers import AutoTokenizer
import torch
from typing import Dict, List, Tuple, Optional
from env.minecraft_client import Agent

class MinecraftRLEnv(gym.Env):
    """
    A Minecraft RL environment that recommends API actions to the LLM.
    The actual execution is handled by the LLM through minecraft_client.py's run function.
    Rewards are obtained from agent.py's reflect function.
    """
    def __init__(
        self,
        max_instruction_length: int = 128,
        max_state_length: int = 256,
        max_history_length: int = 512,
        state_dim: int = 384,
    ):
        super(MinecraftRLEnv, self).__init__()
        
       

        # Set maximum sequence lengths
        self.max_lengths = {
            "instruction": max_instruction_length,
            "state": max_state_length,
            "history": max_history_length,
        }
        
        # Get all available Minecraft API actions
        self.available_actions = self._get_available_actions()
        self.action_space = spaces.Discrete(len(self.available_actions))

        self.state_dim = state_dim
        self.action_dim = len(self.available_actions)
        
    def _get_available_actions(self) -> List[str]:
        """Get all available Minecraft API actions"""
        return [
            "scanNearbyEntities",
            "navigateTo",
            "attackTarget",
            "navigateToBuilding",
            "navigateToAnimal", 
            "navigateToPlayer",
            "UseItemOnEntity",
            "sleep",
            "wake",
            "MineBlock",
            "placeBlock",
            "waitForFeedback",
            "equipItem",
            "tossItem",
            "talkTo",
            "handoverBlock",
            "withdrawItem",
            "storeItem",
            "craftBlock",
            "SmeltingCooking",
            "erectDirtLadder",
            "dismantleDirtLadder",
            "enchantItem",
            "trade",
            "repairItem",
            "eat",
            "drink",
            "wear",
            "layDirtBeam",
            "removeDirtBeam",
            "openContainer",
            "closeContainer",
            "fetchContainerContents",
            "ToggleAction",
            "get_entity_info",
            "get_environment_info",
            "performMovement",
            "lookAt",
            "startFishing",
            "stopFishing",
            "read",
            "readPage",
            "write",
            "mountEntity",
            "dismountEntity",
            "rideEntity",
            "disrideEntity"
        ]
    

    def set_current_state(self, instruction: str, state: str):
        """Update the current instruction and state"""
        self.current_instruction = instruction
        self.current_state = state
        
    def update_reward(self, reward: float):
        """Update reward based on agent's reflect function"""
        self.last_reward = reward
