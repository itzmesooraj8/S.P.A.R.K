from playwright.sync_api import sync_playwright

class BrowserEye:
    def __init__(self, headless=True):
        self.headless = headless
        print(f"🌐 Browser Module Initialized (Headless: {self.headless})")

    def visit(self, url):
        """
        Visits a URL and returns the text content.
        """
        print(f"🌐 [Browser] Visiting: {url}")
        content = ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded")
                
                # Get the text content of the body
                # We can also take screenshots here using page.screenshot()
                content = page.inner_text("body")
                title = page.title()
                
                print(f"✅ [Browser] Loaded '{title}'")
                browser.close()
                return f"Title: {title}\n\nContent Snippet:\n{content[:2000]}..." # Returning first 2000 chars
        
        except Exception as e:
            print(f"❌ [Browser] Error: {e}")
            return f"Error visiting {url}: {e}"

# Singleton can be created on demand
