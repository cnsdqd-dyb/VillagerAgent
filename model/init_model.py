from model.google_model import GoogleLanguageModel
from model.openai_models import OpenAILanguageModel
from model.zhipu_model import ZhipuLanguageModel
from model.huggingface_model import HFLanguageModel
from model.vllm_model import VLLMLanguageModel

def init_language_model(args: dict):
    api_model = args.get("api_model", "")

    if "gpt" in api_model and 'llama' not in api_model or "qwen" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "api_base": args.get("api_base", None),
            "evaluation_strategy": args.get("evaluation_strategy", None),
            "enable_ReAct_prompting": args.get("enable_ReAct_prompting", None),
            "strategy": args.get("strategy", None),
            "role_name": args.get("role_name", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        return OpenAILanguageModel(**new_args)
    elif "gemini" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "role_name": args.get("role_name", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        return GoogleLanguageModel(**new_args)
    elif "glm" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "role_name": args.get("role_name", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        return ZhipuLanguageModel(**new_args)
    elif "vllm" in api_model or "llama" in api_model or "NAS" in api_model:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "api_base": args.get("api_base", None),
            "role_name": args.get("role_name", None),
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        print(f"Loading VLLM model with args: {new_args}")
        return VLLMLanguageModel(**new_args)
    else:
        new_args = {
            "api_key": args.get("api_key", None),
            "api_model": api_model,
            "model_tokenizer": args.get("model_tokenizer", None),
            "verbose": args.get("verbose", None),
            "api_key_list": args.get("api_key_list", None)
        }
        new_args = {k: v for k, v in new_args.items() if v is not None}
        return HFLanguageModel(**new_args)