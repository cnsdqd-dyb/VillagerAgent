import json
import logging
import os
import time
import random
from retry import retry
from zhipuai import ZhipuAI

from model.abstract_language_model import AbstractLanguageModel
from model.utils import extract_info

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ZhipuLanguageModel(AbstractLanguageModel):
    _supported_models = ["glm-4", "glm-3-turbo"]
    def __init__(self, api_key="", api_model="glm-4", role_name="", api_key_list=[]):
        if api_key == "":
            self.api_key = os.environ.get("ZHIPU_API_KEY")
        else:
            self.api_key = api_key

        if api_model in ZhipuLanguageModel._supported_models:
            self.api_model = api_model
        else:
            raise Exception(f"only support {ZhipuLanguageModel._supported_models}, but got {api_model}")

        self.api_key_list = api_key_list

        self.role_name = role_name

        self.cache_path = "zhipu.cache"

        # 统计相关
        if not os.path.exists("data"):
            os.mkdir("data")
        if not os.path.exists("data/zhipu.logs"):
            with open("data/zhipu.logs", "w") as log_file:
                log_file.write("")

        if not os.path.exists("data/tokens.json"):
            with open("data/tokens.json", "w") as token_file:
                init_data = {
                    "dates": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "tokens_used": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "successful_requests": 0,
                    "total_cost": 0,
                    "action_cost": 0,
                }
                json.dump(init_data, token_file)

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

    def generate_thoughts(self, state, k):
        pass

    def evaluate_states(self, states):
        pass

    @retry(tries=5, delay=10, backoff=2, max_delay=60)
    def few_shot_generate_thoughts(self, system_prompt: str = "", example_prompt: [str] or str = [], max_tokens=2048,
                                   temperature=0.01, top_p=0.7, top_k=1, stop: [str]=None, cache_enabled=True, api_model="", check_tags=[],
                                   json_check=False):
        assert 0.0 < temperature < 1.0, "temperature should be in (0.0, 1.0)"
        assert 0.0 < top_p < 1.0, "top_p should be in (0.0, 1.0)"
        if api_model == "":
            api_model = self.api_model
        else:
            if api_model not in ZhipuLanguageModel._supported_models:
                raise Exception(f"only support {ZhipuLanguageModel._supported_models}, but got {api_model}")

        if isinstance(example_prompt, str):
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
            messages = [{"role": "system", "content": system_prompt}]
            for i in range(len(example_prompt)):
                if i % 2 == 0:
                    messages.append({"role": "user", "content": example_prompt[i]})
                else:
                    messages.append({"role": "assistant", "content": example_prompt[i]})

            self.client = ZhipuAI(api_key=random.choice(self.api_key_list))

            response = self.client.chat.completions.create(
                model=api_model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
            )

            content = response.choices[0].message.content
            usage = response.usage
            with open("data/tokens.json", "r") as token_file:
                tokens = json.load(token_file)

            tokens["dates"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            tokens["tokens_used"] += usage.total_tokens
            tokens["prompt_tokens"] += usage.prompt_tokens
            tokens["completion_tokens"] += usage.completion_tokens
            tokens["successful_requests"] += 1

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

            with open("data/zhipu.logs", "a") as log_file:
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
            return content
        except Exception as e:
            logger.warning("Something went wrong on Zhipu's end")
            logger.warning(e)
            logger.warning(e.__cause__)
            raise e


