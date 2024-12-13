from openai import OpenAI

# Modify OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "sk-villageragent"
openai_api_base = "http://10.130.130.13:8000/v1"
temperature = 0.2
max_tokens = 100
frequency_penalty = 0.2
presence_penalty = 0.2
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)
chat_response = client.chat.completions.create(
    model="llama_gptq4/",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke."},
    ],
    temperature=temperature,
    max_tokens=max_tokens,
    frequency_penalty=frequency_penalty,
    presence_penalty=presence_penalty,
)
print("Chat response:", chat_response)