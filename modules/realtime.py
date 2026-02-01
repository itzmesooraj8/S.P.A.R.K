from duckduckgo_search import DDGS

def search_web(query, max_results=3):
    """
    Performs a web search using DuckDuckGo to get real-time information.
    """
    print(f"🌐 [Realtime] Searching the web for: '{query}'...")
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "No results found."
        
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}")
            
        return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Error searching web: {e}"

if __name__ == "__main__":
    # Test
    print(search_web("current time in Tokyo"))
