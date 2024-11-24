import concurrent.futures
import logging
import os
import time
import openai
from openai import OpenAI
import tiktoken
from model.abstract_language_model import AbstractLanguageModel
import json
from retry import retry
import random
import httpx
import base64

from model.utils import extract_info

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OpenAILanguageModel(AbstractLanguageModel):
    _supported_models = ["gpt-4o", "gpt-4-0125-preview", "gpt-4-1106-preview", "gpt-4", "gpt-4-0314", "gpt-4-0613", "gpt-4-32k", "gpt-4-32k-0314",
                         "gpt-4-32k-0613", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-0301",
                         "gpt-3.5-turbo-0613", "gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-instruct"]

    def __init__(self, api_key="", api_model="gpt-3.5-turbo-1106", evaluation_strategy="value", api_base="https://api.openai.com/v1/",
                 enable_ReAct_prompting=True, strategy="cot", role_name="", api_key_list=[]):
        if api_key == "" or api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key != "":
            openai.api_key = api_key
        else:
            raise Exception("Please provide OpenAI API key")
        self.api_key = api_key

        if api_key_list != []:
            self.api_key_list = list(set(api_key_list))
        else:
            self.api_key_list = [api_key]

        if api_base == "" or api_base is None:
            api_base = os.environ.get(
                "OPENAI_API_BASE", ""
            )  # if not set, use the default base path of "https://api.openai.com/v1"
        if api_base != "":
            # e.g. https://api.openai.com/v1/ or your custom url
            openai.api_base = api_base
            # logger.info(f"Using custom api_base {api_base}")
        self.api_base = api_base
        if api_model == "" or api_model is None:
            api_model = os.environ.get("OPENAI_API_MODEL", "")
        if api_model != "":
            if api_model not in OpenAILanguageModel._supported_models:
                raise Exception(
                    f"only support {OpenAILanguageModel._supported_models}, but got {api_model}"
                )

            self.api_model = api_model
        else:
            self.api_model = "gpt-3.5-turbo-1106"
        # logger.info(f"Using api_model {self.api_model}")

        self.use_chat_api = "gpt" in self.api_model
        self.role_name = role_name
        if self.role_name != "":
            if not os.path.exists("ui/logs"):
                os.mkdir("ui/logs")
            file_name = f"ui/logs/{role_name}.json"
            self.log_file = open(file_name, "w")
            self.log_file.write("[]")
            self.log_file.close()

        # reference : https://www.promptingguide.ai/techniques/react
        self.ReAct_prompt = ""
        if enable_ReAct_prompting:
            self.ReAct_prompt = "Write down your observations in format 'Observation:xxxx', then write down your thoughts in format 'Thoughts:xxxx'."

        self.strategy = strategy
        self.evaluation_strategy = evaluation_strategy

        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=random.choice(self.api_key_list) if len(self.api_key_list) > 0 else self.api_key,
            base_url=self.api_base,
            max_retries=5,
        )

        if not os.path.exists("data"):
            os.mkdir("data")
        if not os.path.exists("data/openai.logs"):
            with open("data/openai.logs", "w") as log_file:
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

    def generate_thoughts(self, state, k):
        pass

    def evaluate_states(self, states):
        pass

    def cache_api_call_handler(self, prompt, max_tokens, temperature, k=1, stop=None):
        if os.path.exists(".cache"):
            if not os.path.exists(".cache/openai.cache"):
                with open(".cache/openai.cache", "w") as cache_file:
                    json.dump({}, cache_file)
                return None

            with open(".cache/openai.cache", "r") as cache_file:
                cache = json.load(cache_file)
        else:
            os.mkdir(".cache")
            with open(".cache/openai.cache", "w") as cache_file:
                json.dump({}, cache_file, indent=4)
            cache = {}

        if prompt in cache:
            return cache[prompt]
        else:
            return None

    def save_cache(self, prompt, response):
        if os.path.exists(".cache"):
            if not os.path.exists(".cache/openai.cache"):
                with open(".cache/openai.cache", "w") as cache_file:
                    json.dump({}, cache_file, indent=4)
                return None
            with open(".cache/openai.cache", "r") as cache_file:
                cache = json.load(cache_file)
        else:
            os.mkdir(".cache")
            with open(".cache/openai.cache", "w") as cache_file:
                json.dump({}, cache_file, indent=4)
            cache = {}

        cache[prompt] = response
        with open(".cache/openai.cache", "w") as cache_file:
            json.dump(cache, cache_file, indent=4)


    def update_token_usage(self, prompt_tokens, completion_tokens):
        with open("data/tokens.json", "r") as token_file:
            tokens = json.load(token_file)
        tokens["dates"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        tokens["tokens_used"] += prompt_tokens + completion_tokens
        tokens["prompt_tokens"] += prompt_tokens
        tokens["completion_tokens"] += completion_tokens
        tokens["successful_requests"] += 1
        if self.api_model == "gpt-3.5-turbo":
            tokens["total_cost"] += 0.001 * prompt_tokens * 0.001 + 0.0002 * completion_tokens * 0.001
        if self.api_model == "gpt-4":
            tokens["total_cost"] += 0.03 * prompt_tokens * 0.001 + 0.06 * completion_tokens * 0.001
        if self.api_model == "gpt-4-turbo":
            tokens["total_cost"] += 0.01 * prompt_tokens * 0.001 + 0.03 * completion_tokens * 0.001

        with open("data/tokens.json", "w") as token_file:
            json.dump(tokens, token_file)

    def guard_token_number(self, messages, encoding_name, max_output_tokens=2048) -> [str]:
        text = "".join([message["content"] for message in messages])
        num_tokens = self.num_tokens_from_string(text, encoding_name)
        # logger.info(f"api {encoding_name} num_tokens {num_tokens}")
        if self.api_model == "gpt-4-1106-preview" or self.api_model == "gpt-4-0125-preview":
            if num_tokens >= 1024 * 128 - max_output_tokens:
                logger.warning(f"num_tokens {num_tokens} auto resize waiting please")
            return self.resizing_token(1024 * 128 - max_output_tokens, encoding_name, messages)
        elif self.api_model == "gpt-4":
            if num_tokens >= 1024 * 8 - max_output_tokens:
                logger.warning(f"num_tokens {num_tokens} auto resize waiting please")
            return self.resizing_token(1024 * 8 - max_output_tokens, encoding_name, messages)
        elif self.api_model == "gpt-4-32k":
            if num_tokens >= 1024 * 32 - max_output_tokens:
                logger.warning(f"num_tokens {num_tokens} auto resize waiting please")
            return self.resizing_token(1024 * 32 - max_output_tokens, encoding_name, messages)
        elif self.api_model == "gpt-3.5-turbo-16k" or self.api_model == "gpt-3.5-turbo-1106":
            if num_tokens >= 1024 * 16 - max_output_tokens:
                logger.warning(f"num_tokens {num_tokens} auto resize waiting please")
            return self.resizing_token(1024 * 16 - max_output_tokens, encoding_name, messages)
        elif self.api_model == "gpt-3.5-turbo-instruct":
            if num_tokens >= 1024 * 4 - max_output_tokens:
                logger.warning(f"num_tokens {num_tokens} auto resize waiting please")
            return self.resizing_token(1024 * 4 - max_output_tokens, encoding_name, messages)
        else:
            logger.warning(f"num_tokens {num_tokens} auto resize waiting please")
            return self.resizing_token(1024 * 8 - max_output_tokens, encoding_name, messages)

    def resizing_token(self, target_text_num, encoding_name, messages: [str]) -> [str]:
        while True:
            text = "".join([message["content"] for message in messages])
            num_tokens = self.num_tokens_from_string(text, encoding_name)
            if num_tokens > target_text_num:
                if len(messages[-1]["content"]) < 100:
                    messages.pop()
                else:
                    messages[-1]["content"] = messages[-1]["content"][:-100]
            else:
                break
        return messages

    def num_tokens_from_string(self, string: str, encoding_name: str) -> int:
        encoding = tiktoken.encoding_for_model(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def gpt_api(self, messages: list, model: str, temperature: float):
        """为提供的对话消息创建新的回答

        Args:
            messages (list): 完整的对话消息
        """
        # logger.info("api")
        start_time = time.time()
        completion = self.client.chat.completions.create(model=model, messages=messages, temperature=temperature)
        # logger.warning(completion.choices[0].message.content)
        logger.debug(f"Time taken: {time.time() - start_time}")
        return completion
    
    def gpt_api_stream(self, messages: list, model: str, temperature: float):
        """为提供的对话消息创建新的回答 (流式传输)

        Args:
            messages (list): 完整的对话消息
        """
        # logger.info("streaming api")
        start_time = time.time()
        content = ""
        # print(messages)
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                # print(chunk.choices[0].delta.content, end="")
                content += chunk.choices[0].delta.content
        logger.debug(f"Time taken: {time.time() - start_time}")
        return content

    @retry(tries=10, delay=5, backoff=2, max_delay=60)
    def few_shot_generate_thoughts(self, system_prompt: str = "", example_prompt: [str] or str = [], max_tokens=1024,
                                   temperature=0.0, k=1, stop=None, cache_enabled=True, api_model="", check_tags=[],
                                   json_check=False, stream=True):
        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=random.choice(self.api_key_list) if len(self.api_key_list) > 0 else self.api_key,
            base_url=self.api_base,
            max_retries=5,
        )
        if api_model == "":
            api_model = self.api_model
        else:
            if api_model not in OpenAILanguageModel._supported_models:
                raise Exception(f"only support {OpenAILanguageModel._supported_models}, but got {api_model}")
        if type(example_prompt) == str:
            example_prompt = [example_prompt]
        assert self.use_chat_api == True, "few shot generation only support chat api"
        assert len(example_prompt) % 2 == 1 or len(example_prompt) == 0, "example prompt should be odd number or empty"

        # logger.info("waiting for generating thoughts") 
        # logger.info(f"using api model {api_model}")
        prompt = str(system_prompt) + "\n" + "\n".join(example_prompt)
        if cache_enabled:
            content = self.cache_api_call_handler(prompt, max_tokens, temperature, k, stop)
            if content is not None:
                if self.role_name:
                    try:
                        with open(f"ui/logs/{self.role_name}.json", "r") as log_file:
                            logs = json.load(log_file)
                        logs.append({"prompt": prompt, "response": content})
                        with open(f"ui/logs/{self.role_name}.json", "w") as log_file:
                            json.dump(logs, log_file)
                    except Exception as e:
                        with open(f"ui/logs/{self.role_name}.json", "w") as log_file:
                            json.dump([], log_file)
                return content
        start_time = time.time()
        while True:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                for i in range(len(example_prompt)):
                    if i % 2 == 0:
                        messages.append({"role": "user", "content": example_prompt[i]})
                    else:
                        messages.append({"role": "assistant", "content": example_prompt[i]})

                # dynamic change timeout by token number
                messages = self.guard_token_number(messages, api_model, max_tokens)
 
                if stream:
                    content = self.gpt_api_stream(messages, api_model, temperature)
                    usage_data = {"prompt_tokens": self.num_tokens_from_string(prompt, api_model),
                             "completion_tokens": self.num_tokens_from_string(content, api_model)}
                    self.update_token_usage(usage_data["prompt_tokens"], usage_data["completion_tokens"])
                else:
                    response = self.gpt_api(messages, api_model, temperature)

                    self.update_token_usage(response.usage.prompt_tokens, response.usage.completion_tokens)

                    content = response.choices[0].message.content

                for tag in check_tags:
                    if tag not in content:
                        raise Exception(f"tag {tag} not in content {content}")
                if json_check:
                    if len(extract_info(content)) == 0:
                        raise Exception(f"content {content} is not json")
                if cache_enabled:
                    self.save_cache(prompt, content)
                with open("data/openai.logs", "a") as log_file:
                    log_file.write(
                        "\n" + "-----------" + "\n" + "Prompt : " + str(messages) + "\n"
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

                # logger.info(f"LLM API Time taken: {time.time() - start_time}")
                if os.path.exists("data/llm_inference.json"):
                    with open("data/llm_inference.json", "r") as log_file:
                        log = json.load(log_file)
                    log["time"] += time.time() - start_time
                    with open("data/llm_inference.json", "w") as log_file:
                        json.dump(log, log_file)
                return content
            
            except openai.APIConnectionError as e:
                logger.warning("[Proxy] The server could not be reached")
                # logger.warning(e.__cause__)  # an underlying Exception, likely raised within httpx.
                

            except openai.RateLimitError as e:
                sleep_duratoin = os.environ.get("OPENAI_RATE_TIMEOUT", 30)
                logger.warning("A 429 status code was received; we should back off a bit.")
                # time.sleep(sleep_duratoin)
                raise e

            except openai.APIStatusError as e:
                logger.warning("[Proxy] Another non-200-range status code was received")
                logger.warning(e.status_code)

                if e.status_code == 403:
                    # API KEY expired, remove it from the list
                    if self.api_key in self.api_key_list:
                        self.api_key_list.remove(self.api_key)
                logger.warning(e.response)
                self.client = OpenAI(
                    # This is the default and can be omitted
                    api_key=random.choice(self.api_key_list) if len(self.api_key_list) > 0 else self.api_key,
                    base_url=self.api_base,
                    max_retries=5,
                )
    

            except openai.InternalServerError as e:
                logger.warning("Something went wrong on OpenAI's end")
                logger.warning(e.status_code)
                logger.warning(e.response)
                raise e

            except Exception as e:
                logger.warning("Something other than an HTTP error occurred")
                logger.warning(e)
                logger.warning(e.__cause__)
                raise e
            
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @retry(tries=10, delay=5, backoff=2, max_delay=60)
    def generate_with_image(self, prompt_before_image: [str] or str, image_path: str, prompt_after_image: [str] or str="", system_prompt: str=None, max_tokens: int=-1,
                 temperature: float=0.0, k: int=1, stop=None, cache_enabled: bool=True, api_model: str="",
                 check_tags: list=[], json_check: bool=False, stream: bool=True):
        
        self.client = OpenAI(
            api_key=random.choice(self.api_key_list) if len(self.api_key_list) > 0 else self.api_key,
            base_url=self.api_base,
            max_retries=5,
        )
        
        if api_model == "":
            api_model = self.api_model
        else:
            if api_model not in OpenAILanguageModel._supported_models:
                raise Exception(f"only support {OpenAILanguageModel._supported_models}, but got {api_model}")
        
        if type(prompt_before_image) == str:
            prompt_before_image = [prompt_before_image]
        if type(prompt_after_image) == str:
            prompt_after_image = [prompt_after_image]
        
        assert self.use_chat_api, "few shot generation only support chat api"

        # Concatenate the prompts and image URL into the message structure
        if system_prompt is None:
            system_prompt = "You are a helpful assistant."
        messages = [{"role": "system", "content": system_prompt}]
        for prompt in prompt_before_image:
            messages.append({"role": "user", "content": prompt})
        
        # Getting the base64 string
        base64_image = self.encode_image(image_path)
        if ".jpg" in image_path:
            url = f"data:image/jpeg;base64,{base64_image}"
        elif ".png" in image_path:
            url = f"data:image/png;base64,{base64_image}"
        else:
            raise Exception("Image format not supported")
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "This is an image:"},
                {"type": "image_url", "image_url": {"url": url}}
            ]
        })
        
        for prompt in prompt_after_image:
            messages.append({"role": "user", "content": prompt})
        
        
        if cache_enabled:
            prompt = str(system_prompt) + "\n" + "\n".join(prompt_before_image + prompt_after_image)
            content = self.cache_api_call_handler(prompt, max_tokens, temperature, k, stop)
            if content is not None:
                return content
        
        start_time = time.time()
        while True:
            try:
                if stream:
                    content = self.gpt_api_stream(messages, api_model, temperature)
                    usage_data = {"prompt_tokens": self.num_tokens_from_string(prompt, api_model),
                                    "completion_tokens": self.num_tokens_from_string(content, api_model)}
                    self.update_token_usage(usage_data["prompt_tokens"], usage_data["completion_tokens"])
                else:
                    response = self.gpt_api(messages, api_model, temperature)
                    self.update_token_usage(response.usage.prompt_tokens, response.usage.completion_tokens)
                    content = response.choices[0].message.content

                for tag in check_tags:
                    if tag not in content:
                        raise Exception(f"tag {tag} not in content {content}")
                if json_check:
                    if len(extract_info(content)) == 0:
                        raise Exception(f"content {content} is not json")
                if cache_enabled:
                    self.save_cache(prompt, content)
                with open("data/openai.logs", "a") as log_file:
                    log_file.write(
                        "\n" + "-----------" + "\n" + "Prompt : " + str(messages) + "\n"
                    )

                if os.path.exists("data/llm_inference.json"):
                    with open("data/llm_inference.json", "r") as log_file:
                        log = json.load(log_file)
                    log["time"] += time.time() - start_time
                    with open("data/llm_inference.json", "w") as log_file:
                        json.dump(log, log_file)
                return content

            except openai.APIConnectionError as e:
                logger.warning("[Proxy] The server could not be reached")

            except openai.RateLimitError as e:
                sleep_duratoin = os.environ.get("OPENAI_RATE_TIMEOUT", 30)
                logger.warning("A 429 status code was received; we should back off a bit.")
                raise e

            except openai.APIStatusError as e:
                logger.warning("[Proxy] Another non-200-range status code was received")
                logger.warning(e.status_code)
                if e.status_code == 403:
                    if self.api_key in self.api_key_list:
                        self.api_key_list.remove(self.api_key)
                logger.warning(e.response)
                self.client = OpenAI(
                    api_key=random.choice(self.api_key_list) if len(self.api_key_list) > 0 else self.api_key,
                    base_url=self.api_base,
                    max_retries=5,
                )

            except openai.InternalServerError as e:
                logger.warning("Something went wrong on OpenAI's end")
                logger.warning(e.status_code)
                logger.warning(e.response)
                raise e

            except Exception as e:
                logger.warning("Something other than an HTTP error occurred")
                logger.warning(e)
                logger.warning(e.__cause__)
                raise e
               

