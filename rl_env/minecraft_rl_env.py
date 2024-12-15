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
        tokenizer_name: str = "gpt2",
        max_instruction_length: int = 128,
        max_state_length: int = 256,
        max_history_length: int = 512,
        state_dim: int = 384,
    ):
        super(MinecraftRLEnv, self).__init__()
        
        # Initialize tokenizer
        MODELS = [
            ('xlm-mlm-enfr-1024'   ,"XLMModel"),
            ('distilbert-base-cased', "DistilBertModel"),
            ('bert-base-uncased'     ,"BertModel"),
            ('roberta-base'        ,"RobertaModel"),
            ("cardiffnlp/twitter-roberta-base-sentiment","RobertaSentTW"),
            ('xlnet-base-cased'     ,"XLNetModel"),
            ('transfo-xl-wt103'    ,"TransfoXLModel"),
            ('bert-base-cased'       ,"BertModelUncased"),
            ('xlm-roberta-base'     ,"XLMRobertaModel"),
            ('openai-gpt'           ,"OpenAIGPTModel"),
            ('gpt2'                 ,"GPT2Model")
        ]

        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        self.vocab_size = 50257
        if self.tokenizer.pad_token is None:
            self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})

        # Set maximum sequence lengths
        self.max_lengths = {
            "instruction": max_instruction_length,
            "state": max_state_length,
            "history": max_history_length,
        }
        
        # Get all available Minecraft API actions
        self.available_actions = self._get_available_actions()
        self.action_space = spaces.Discrete(len(self.available_actions))
        
        # Define observation space (tokenized text inputs)
        self.observation_space = spaces.Dict({
            "instruction": spaces.Box(
                low=0,
                high=len(self.tokenizer),
                shape=(max_instruction_length,),
                dtype=np.int64
            ),
            "state": spaces.Box(
                low=0,
                high=len(self.tokenizer),
                shape=(max_state_length,),
                dtype=np.int64
            ),
            "history": spaces.Box(
                low=0,
                high=len(self.tokenizer),
                shape=(max_history_length,),
                dtype=np.int64
            )
        })

        self.state_dim = state_dim
        self.action_dim = len(self.available_actions)
        
        # Initialize state
        self.reset()
        
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
    
    def _tokenize_text(self, text: str, max_length: int) -> np.ndarray:
        """Tokenize text and pad/truncate to max_length"""
        tokens = self.tokenizer.encode(
            text,
            add_special_tokens=True,
            max_length=max_length,
            padding="max_length",
            truncation=True,
            return_tensors="np"
        )
        return tokens[0]  # Remove batch dimension
    
    def reset(self) -> Dict[str, np.ndarray]:
        """Reset the environment"""
        self.current_instruction = ""
        self.current_state = ""
        self.action_history = ""
        self.last_action = None
        self.last_reward = 0.0
        
        return self._get_observation()
    
    def _get_observation(self) -> Dict[str, np.ndarray]:
        """Get the current observation as tokenized text"""
        return {
            "instruction": self._tokenize_text(
                self.current_instruction,
                self.max_lengths["instruction"]
            ),
            "state": self._tokenize_text(
                self.current_state,
                self.max_lengths["state"]
            ),
            "history": self._tokenize_text(
                self.action_history,
                self.max_lengths["history"]
            )
        }
    
    def token_current_state(self, instruction: str, basic_state: str):
        """Tokenize the current instruction and state"""
        self.current_instruction = instruction
        self.current_state = basic_state

        instruction_tokens = self._tokenize_text(
            instruction,
            self.max_lengths["instruction"]
        )
        state_tokens = self._tokenize_text(
            basic_state,
            self.max_lengths["state"]
        )
        return instruction_tokens, state_tokens
    
    def token_current_action_observation(self, action, observation): 
        """Tokenize the current instruction and state"""
        action_observation = f"Action: {action['log']}\nObservation: {observation}"

        action_observation_tokens = self._tokenize_text(
            action_observation,
            self.max_lengths["history"]
        )
        return action_observation_tokens
    
    def set_current_state(self, instruction: str, state: str):
        """Update the current instruction and state"""
        self.current_instruction = instruction
        self.current_state = state
        
    def update_reward(self, reward: float):
        """Update reward based on agent's reflect function"""
        self.last_reward = reward
