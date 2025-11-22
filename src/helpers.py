from openai import OpenAI

def get_active_model(base_url="http://localhost:1234/v1", api_key="lm-studio"):
    """
    Send a test payload to the openAI endpoint to get the name of the 
    active model. 
    """
    
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
    
def fetch_models(base_url="http://localhost:1234/v1", api_key="lm-studio"):
    """
    Return model list from an openAI compatible 
    endpoint. 
    """

    client = OpenAI(base_url=base_url, api_key=api_key)
    try:
        response = client.models.list()
        return response
    except Exception as e:
        return e
    
def is_embedding(model_name: str) -> bool:
    """
    Helper func to filter out embedding models. 
    Can be expanded for more options. 
    """

    keywords = ["embed", "embedding", "bert", "nomic", "all-minilm"]

    name_lower = model_name.lower()
    return any(keyword in name_lower for keyword in keywords)