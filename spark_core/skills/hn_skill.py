import httpx
from spark_core.skills.base import Skill

class HackerNewsSkill(Skill):
    name = "hackernews_skill"
    description = "Fetches the top stories from HackerNews to provide live tech world awareness."

    async def execute(self, **kwargs) -> dict:
        limit = kwargs.get("limit", 5)
        print(f"🌐 [HackerNewsSkill] Fetching top {limit} stories...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                top_r = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
                if top_r.status_code != 200:
                    return {"success": False, "error": "Failed to fetch top stories"}
                
                story_ids = top_r.json()[:limit]
                stories = []
                for sid in story_ids:
                    item_r = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                    if item_r.status_code == 200:
                        stories.append(item_r.json())
                
                return {
                    "success": True,
                    "count": len(stories),
                    "stories": [{"title": s.get("title"), "url": s.get("url")} for s in stories]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
