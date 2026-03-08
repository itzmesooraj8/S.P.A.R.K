"""
SPARK Browser Agent — Playwright-Powered Autonomous Web Browser
────────────────────────────────────────────────────────────────────────────────
Gives SPARK the ability to autonomously browse the web, extract information,
take screenshots, and perform web-based research.

Features:
  - POST /api/browser/navigate      — navigate to URL + get content
  - POST /api/browser/screenshot    — capture page screenshot (base64)
  - POST /api/browser/search        — DuckDuckGo web search
  - POST /api/browser/extract       — extract text/links from URL
  - POST /api/browser/interact      — click/type/scroll on page
  - GET  /api/browser/history       — browsing history
  - POST /api/browser/close         — close the browser instance
  - GET  /api/browser/status        — browser status
  - Live screenshot push: every 2s while browser active (via /ws/system)
"""

import asyncio
import base64
import time
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ws.manager import ws_manager

# ── Browser State ──────────────────────────────────────────────────────────────
_browser = None
_context = None
_page    = None
_history: List[Dict] = []
_browser_lock = asyncio.Lock()

# ── Screenshot Push State ──────────────────────────────────────────────────────
_active_operation_id: Optional[str] = None  # Identifies current browser operation
_screenshot_push_task: Optional[asyncio.Task] = None


async def _get_page():
    """Lazily initialize Playwright browser and return active page."""
    global _browser, _context, _page

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise HTTPException(status_code=503, detail="Playwright not installed. Run: playwright install chromium")

    if _page is None or _page.is_closed():
        async with _browser_lock:
            if _page is None or _page.is_closed():
                pw = await async_playwright().start()
                _browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                _context = await _browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (compatible; SPARK-AI-Agent/1.0)"
                )
                _page = await _context.new_page()
                print("🌐 [BROWSER] Playwright chromium launched.")

    return _page


def _add_history(url: str, title: str, action: str):
    _history.append({
        "id":         str(uuid.uuid4()),
        "url":        url,
        "title":      title,
        "action":     action,
        "timestamp":  time.time(),
    })
    # Keep last 100 entries
    if len(_history) > 100:
        _history[:] = _history[-100:]


async def _start_screenshot_push_loop(operation_id: str):
    """
    Background loop: capture screenshot every 2 seconds while browser is active.
    Push to /ws/system as BROWSER_LIVE_PREVIEW events.
    Stops when operation_id changes or browser closes.
    """
    global _page, _active_operation_id
    
    while _active_operation_id == operation_id:
        try:
            if _page is None or _page.is_closed():
                break
            
            # Capture screenshot
            screenshot_bytes = await _page.screenshot(full_page=False, type="jpeg", quality=75)
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            current_url = _page.url
            
            # Push via WebSocket
            await ws_manager.broadcast_json({
                "type": "BROWSER_LIVE_PREVIEW",
                "operation_id": operation_id,
                "url": current_url,
                "screenshot_base64": f"data:image/jpeg;base64,{b64}",
                "timestamp": time.time() * 1000,
            }, "system")
            
            # Wait 2 seconds before next capture
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"⚠️ [BROWSER] Screenshot push error: {exc}")
            await asyncio.sleep(2)


# ── FastAPI Router ─────────────────────────────────────────────────────────────
browser_router = APIRouter(prefix="/api/browser", tags=["browser"])


class NavigateRequest(BaseModel):
    url: str
    wait_until: str = "networkidle"   # load / domcontentloaded / networkidle
    timeout_ms: int = 30000
    extract_text: bool = True
    extract_links: bool = False


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


class ScreenshotRequest(BaseModel):
    url: Optional[str] = None         # Navigate to URL first if provided
    full_page: bool = False
    format: str = "png"               # png / jpeg


class ExtractRequest(BaseModel):
    url: str
    selector: Optional[str] = None   # CSS selector to extract specific element
    extract_text: bool = True
    extract_links: bool = True
    extract_images: bool = False


class InteractRequest(BaseModel):
    action: str                        # click / type / scroll / press / hover
    selector: str
    value: Optional[str] = None       # For type action
    url: Optional[str] = None         # Navigate first if provided


@browser_router.get("/status")
async def browser_status():
    """Check browser agent status."""
    global _page, _browser
    is_running = _page is not None and not _page.is_closed()
    current_url = None
    if is_running:
        try:
            current_url = _page.url
        except Exception:
            pass

    try:
        from playwright.async_api import async_playwright
        playwright_available = True
    except ImportError:
        playwright_available = False

    return {
        "available":       playwright_available,
        "browser_running": is_running,
        "current_url":     current_url,
        "history_count":   len(_history),
    }


@browser_router.post("/navigate")
async def navigate(req: NavigateRequest):
    """Navigate to a URL and return page content. Starts live screenshot stream."""
    global _active_operation_id, _screenshot_push_task
    try:
        page = await _get_page()

        # Assign operation ID for this browser session
        operation_id = str(uuid.uuid4())
        _active_operation_id = operation_id
        
        # Start screenshot push loop (if not already running for this operation)
        if _screenshot_push_task is None or _screenshot_push_task.done():
            _screenshot_push_task = asyncio.create_task(_start_screenshot_push_loop(operation_id))

        await page.goto(
            req.url,
            wait_until=req.wait_until,
            timeout=req.timeout_ms,
        )

        title = await page.title()
        result: Dict[str, Any] = {
            "url":   page.url,
            "title": title,
            "status": "ok",
            "operation_id": operation_id,  # Include operation ID for tracking
        }

        if req.extract_text:
            text = await page.evaluate("() => document.body.innerText")
            # Limit to 8000 chars for API response
            result["text"] = text[:8000] if text else ""
            result["text_length"] = len(text) if text else 0

        if req.extract_links:
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({ href: a.href, text: a.innerText.trim() }))
                    .filter(l => l.href.startsWith('http'))
                    .slice(0, 50)
            """)
            result["links"] = links

        _add_history(page.url, title, "navigate")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Navigation failed: {str(e)}")


@browser_router.post("/screenshot")
async def screenshot(req: ScreenshotRequest):
    """Take a screenshot of the current page or a specific URL."""
    try:
        page = await _get_page()

        if req.url:
            await page.goto(req.url, wait_until="networkidle", timeout=30000)

        screenshot_bytes = await page.screenshot(
            full_page=req.full_page,
            type=req.format,
        )

        title = await page.title()
        b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        _add_history(page.url, title, "screenshot")
        return {
            "url":    page.url,
            "title":  title,
            "image":  f"data:image/{req.format};base64,{b64}",
            "width":  1280,
            "height": 800,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")


@browser_router.post("/search")
async def web_search(req: SearchRequest):
    """Perform a DuckDuckGo web search and return results."""
    try:
        page = await _get_page()

        search_url = f"https://html.duckduckgo.com/html/?q={req.query.replace(' ', '+')}"
        await page.goto(search_url, wait_until="networkidle", timeout=30000)

        # Extract search results
        results = await page.evaluate(f"""
            () => {{
                const items = [];
                const results = document.querySelectorAll('.result');
                const maxResults = {req.max_results};
                for (let i = 0; i < Math.min(results.length, maxResults); i++) {{
                    const r = results[i];
                    const titleEl = r.querySelector('.result__title a');
                    const snippetEl = r.querySelector('.result__snippet');
                    const urlEl = r.querySelector('.result__url');
                    if (titleEl) {{
                        items.push({{
                            title: titleEl.innerText.trim(),
                            url: titleEl.href,
                            snippet: snippetEl ? snippetEl.innerText.trim() : '',
                            displayed_url: urlEl ? urlEl.innerText.trim() : ''
                        }});
                    }}
                }}
                return items;
            }}
        """)

        _add_history(search_url, f"Search: {req.query}", "search")
        return {
            "query":   req.query,
            "results": results,
            "count":   len(results),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@browser_router.post("/extract")
async def extract_content(req: ExtractRequest):
    """Extract structured content from a URL."""
    try:
        page = await _get_page()
        await page.goto(req.url, wait_until="networkidle", timeout=30000)
        title = await page.title()

        result: Dict[str, Any] = {"url": page.url, "title": title}

        if req.selector:
            # Extract specific element
            try:
                el_text = await page.eval_on_selector(req.selector, "el => el.innerText")
                result["element_text"] = el_text
            except Exception:
                result["element_text"] = None

        if req.extract_text:
            text = await page.evaluate("() => document.body.innerText")
            result["text"] = text[:10000] if text else ""

        if req.extract_links:
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({ href: a.href, text: a.innerText.trim() }))
                    .filter(l => l.href.startsWith('http'))
                    .slice(0, 100)
            """)
            result["links"] = links

        if req.extract_images:
            images = await page.evaluate("""
                () => Array.from(document.querySelectorAll('img[src]'))
                    .map(img => ({ src: img.src, alt: img.alt }))
                    .slice(0, 50)
            """)
            result["images"] = images

        _add_history(page.url, title, "extract")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@browser_router.post("/interact")
async def interact(req: InteractRequest):
    """Interact with a page element (click, type, scroll, etc.)."""
    try:
        page = await _get_page()

        if req.url:
            await page.goto(req.url, wait_until="networkidle", timeout=30000)

        if req.action == "click":
            await page.click(req.selector)
        elif req.action == "type":
            await page.fill(req.selector, req.value or "")
        elif req.action == "scroll":
            await page.evaluate(f"document.querySelector('{req.selector}')?.scrollIntoView()")
        elif req.action == "press":
            await page.press(req.selector, req.value or "Enter")
        elif req.action == "hover":
            await page.hover(req.selector)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

        title = await page.title()
        _add_history(page.url, title, f"interact:{req.action}")
        return {"status": "ok", "action": req.action, "url": page.url, "title": title}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interaction failed: {str(e)}")


@browser_router.get("/history")
async def browsing_history(limit: int = 50):
    """Return recent browsing history."""
    recent = sorted(_history, key=lambda h: h.get("timestamp", 0), reverse=True)[:limit]
    return {"history": recent, "total": len(_history)}


@browser_router.post("/close")
async def close_browser():
    """Close the browser instance to free resources."""
    global _browser, _context, _page, _active_operation_id, _screenshot_push_task
    try:
        # Stop screenshot push loop
        _active_operation_id = None
        if _screenshot_push_task and not _screenshot_push_task.done():
            _screenshot_push_task.cancel()
        
        if _page and not _page.is_closed():
            await _page.close()
        if _context:
            await _context.close()
        if _browser:
            await _browser.close()
        _page = None
        _context = None
        _browser = None
        print("🌐 [BROWSER] Browser closed.")
        return {"status": "closed"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
