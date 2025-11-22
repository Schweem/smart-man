from openai import OpenAI

def get_active_model(base_url="http://localhost:1234/v1", api_key="lm-studio"):
    client = OpenAI(base_url=base_url, api_key=api_key)
    try:
        # 1 token request to get info from server
        response = client.chat.completions.create(
            model="local-model", # we use a dummy name to grab whatever it defaults to (generally whatever model is loaded)
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1 # max tokens to make this really short
        )
        return response.model
    except Exception:
        return "No model loaded."