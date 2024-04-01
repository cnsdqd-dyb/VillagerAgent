from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from retry import retry
import os
import json
import tiktoken
from model.utils import extract_info

from model.abstract_language_model import AbstractLanguageModel
import logging
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
import time
class HFLanguageModel:
    def __init__(self, api_key="", api_model="gpt2", model_tokenizer=None, verbose=False, api_key_list=[]):
        self.model = AutoModelForCausalLM.from_pretrained(api_model)
        self.tokenizer = AutoTokenizer.from_pretrained(model_tokenizer or api_model)
        self.verbose = verbose
        self.api_model = api_model

    @retry(tries=5, delay=10, backoff=2, max_delay=60)
    def few_shot_generate_thoughts(self, system_prompt: str = "", example_prompt: [str] or str = [], max_tokens=2048,
                                   temperature=0.0, top_p=1, top_k=1, stop: [str] = None, cache_enabled=True,
                                   api_model="", check_tags=[],
                                   json_check=False):
        if api_model == "":
            api_model = self.api_model
        else:
            # Here you would check if the api_model is supported by Hugging Face

            pass

        if type(example_prompt) == str:
            example_prompt = [example_prompt]

        assert len(example_prompt) % 2 == 1 or len(example_prompt) == 0, "example prompt should be odd number or empty"

        logger.info("waiting for generating thoughts")
        logger.info(f"using api model {api_model}")

        prompt = str(system_prompt) + "\n"
        for i in range(len(example_prompt)):
            prompt += example_prompt[i] + "\n"

        if cache_enabled:
            content = self.cache_api_call_handler(prompt)
            if content is not None:
                if self.role_name:
                    with open(f"ui/logs/{self.role_name}.json", "r") as log_file:
                        logs = json.load(log_file)
                    logs.append({"prompt": prompt, "response": content})
                    with open(f"ui/logs/{self.role_name}.json", "w") as log_file:
                        json.dump(logs, log_file)
                return content

        start_time = time.time()
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(
                **inputs, max_length=max_tokens, temperature=temperature, top_p=top_p, top_k=top_k, num_return_sequences=top_k
            )
            content = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

             # get tokens from prompt
            prompt_tokens = self.num_tokens_from_string(prompt)
            completion_tokens = self.num_tokens_from_string(content)
            tokens_used = prompt_tokens + completion_tokens

            # update tokens
            with open("data/tokens.json", "r") as token_file:
                tokens = json.load(token_file)
            tokens["tokens_used"] += tokens_used
            tokens["prompt_tokens"] += prompt_tokens
            tokens["completion_tokens"] += completion_tokens
            tokens["successful_requests"] += 1
            # tokens["total_cost"] += tokens_used * 0.0000000005
            # tokens["action_cost"] += tokens_used * 0.0000000005
            with open("data/tokens.json", "w") as token_file:
                json.dump(tokens, token_file)

            for tag in check_tags:
                if tag not in content:
                    raise Exception(f"tag {tag} not in content {content}")
            if json_check:
                if len(extract_info(content)) == 0:
                    raise Exception(f"content {content} is not json")

            if cache_enabled:
                self.save_cache(prompt, content)
            with open("data/google.logs", "a") as log_file:
                log_file.write(
                    "\n" + "-----------" + "\n" + "Prompt : " + str(prompt) + "\n"
                )
            if self.role_name:
                if not os.path.exists(f"ui/logs/{self.role_name}.json"):
                    os.makedirs("ui/logs", exist_ok=True)
                    with open(f"ui/logs/{self.role_name}.json", "w") as log_file:
                        json.dump([], log_file)
                with open(f"ui/logs/{self.role_name}.json", "r") as log_file:
                    logs = json.load(log_file)
                logs.append({"prompt": prompt, "response": content})
                with open(f"ui/logs/{self.role_name}.json", "w") as log_file:
                    json.dump(logs, log_file)

            logger.info(f"Time taken: {time.time() - start_time}")
            if os.path.exists("data/llm_inference.json"):
                with open("data/llm_inference.json", "r") as log_file:
                    log = json.load(log_file)
                log["time"] += time.time() - start_time
                with open("data/llm_inference.json", "w") as log_file:
                    json.dump(log, log_file)

            logger.info(f"Time taken: {time.time() - start_time}")
            return content
        except Exception as e:
            logger.warning("Something went wrong on Hugging Face's end")
            logger.warning(e)
            raise e

    def num_tokens_from_string(self, string: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def cache_api_call_handler(self, prompt):
        if os.path.exists(".cache") and os.path.exists(os.path.join(".cache", self.cache_path)):
            with open(os.path.join(".cache", self.cache_path), "r") as cache_file:
                cache = json.load(cache_file)
            if prompt in cache.keys():
                return cache[prompt]
            else:
                return None
        else:
            return None

    def save_cache(self, prompt, response):
        if os.path.exists(".cache"):
            if os.path.exists(os.path.join(".cache", self.cache_path)):
                with open(os.path.join(".cache", self.cache_path), "r") as cache_file:
                    cache = json.load(cache_file)
                cache[prompt] = response
                with open(os.path.join(".cache", self.cache_path), "w") as cache_file:
                    json.dump(cache, cache_file)
            else:
                cache = {prompt: response}
                with open(os.path.join(".cache", self.cache_path), "w") as cache_file:
                    json.dump(cache, cache_file)
        else:
            os.mkdir(".cache")

            cache = {prompt: response}
            with open(os.path.join(".cache", self.cache_path), "w") as cache_file:
                json.dump(cache, cache_file)
