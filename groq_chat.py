import requests
import os

def chat_with_groq(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"  # Correct endpoint
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-70b-8192",  # Use a model you have access to
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    if "choices" in result and result["choices"]:
        return result["choices"][0]["message"]["content"]
    elif "error" in result:
        return f"Groq API error: {result['error']}"
    else:
        return "Sorry, I couldn't get a response from the Groq API."
