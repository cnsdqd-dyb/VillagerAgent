from abc import ABC, abstractmethod


class AbstractLanguageModel(ABC):
    @abstractmethod
    def generate_thoughts(self, state, k):
        pass

    @abstractmethod
    def evaluate_states(self, states):
        pass

    @abstractmethod
    def few_shot_generate_thoughts(self, system_prompt: str, example_prompt: [str] or str, max_tokens: int,
                                   temperature: float, k: int, stop, cache_enabled: bool, api_model: str,
                                   check_tags: list, json_check: bool, stream: bool):
        pass
