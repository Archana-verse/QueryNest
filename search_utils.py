import httpx
import os
from dotenv import load_dotenv

load_dotenv()
SERP_API_KEY = os.getenv("SERP_API_KEY")

# def search_web(query):
#     q = query.lower().replace("search the web for", "").strip()
#     url = f"https://serpapi.com/search.json?q={q}&api_key={SERP_API_KEY}"

#     try:
#         resp = httpx.get(url)
#         results = resp.json().get("organic_results", [])
#         if not results:
#             return "No search results found."

#         top = results[0]
#         return f"{top.get('title')}\n{top.get('snippet')}\n{top.get('link')}"
#     except:
#         return "Failed to search the web."
def search_web(query):
    try:
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "engine": "google"
        }
        res = requests.get("https://serpapi.com/search", params=params)
        data = res.json()
        answer = data.get("answer_box", {}).get("answer") or \
                 data.get("organic_results", [{}])[0].get("snippet", "No snippet found")
        return {"response": answer}
    except:
        return {"response": "❌ Unable to perform web search."}

# def get_weather():
#     try:
#         url = "https://wttr.in/?format=3"
#         return httpx.get(url).text
#     except:
#         return "Failed to fetch weather."
def get_weather():
    try:
        res = requests.get("https://wttr.in/?format=3")
        return {"response": res.text}
    except:
        return {"response": "❌ Unable to fetch weather."}
