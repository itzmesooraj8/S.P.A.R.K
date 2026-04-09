import httpx
from spark_core.skills.base import Skill

class HackerNewsSkill(Skill):
    name = "hn_top_stories"
    description = "Fetches the current top 5 stories from HackerNews to provide live tech world awareness."

    async def execute(self, **kwargs) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                # Fetch top story IDs
                resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
                resp.raise_for_status()
                story_ids = resp.json()[:5]

                stories = []
                for sid in story_ids:
                    story_resp = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                    if story_resp.status_code == 200:
                        stories.append(story_resp.json())

                return {
                    "status": "success",
                    "top_stories": [{"title": s.get("title"), "url": s.get("url")} for s in stories]
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
