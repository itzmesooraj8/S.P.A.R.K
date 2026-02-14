import requests
import os

def web_search(query):
    """Performs a web search using SerpAPI and stores the result in memory (Sticky Search)."""
    from spark.modules.memory import memory_engine
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Web search API key not set."
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": 1
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params)
        data = resp.json()
        if "error" in data:
            return f"Web search error: {data['error']}"
        answer = None
        if "answer_box" in data and "answer" in data["answer_box"]:
            answer = data["answer_box"]["answer"]
        elif "organic_results" in data and data["organic_results"]:
            answer = data["organic_results"][0].get("snippet")
        
        if answer:
            # --- PHASE 4: STICKY SEARCH ---
            memory_engine.add_memory(f"Web Search Result for '{query}': {answer}", {"source": "web_search", "query": query})
            return answer
        
        return "No web search result found."
    except Exception as e:
        return f"Web search error: {e}"
