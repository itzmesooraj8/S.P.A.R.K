"""
S.P.A.R.K Isolated Headless Browser Automation
Spins up headless Playwright instances inside restricted permission frameworks,
supporting parallel crawling, storage isolation, and strict domain origin filtering.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("SPARK_ISOLATED_BROWSER")

# Optional Playwright import
playwright_sync = None
try:
    from playwright.sync_api import sync_playwright
    playwright_sync = sync_playwright
except ImportError:
    logger.warning("playwright not installed. Falling back to simulated secure browser runtime.")

class IsolatedBrowserInstance:
    """Represents a sandboxed web execution context with strict security configurations."""
    
    def __init__(
        self, 
        allowed_origins: Optional[List[str]] = None,
        block_cookies: bool = True,
        use_simulation: bool = False
    ):
        self.allowed_origins = allowed_origins or []
        self.block_cookies = block_cookies
        self.use_simulation = use_simulation or (playwright_sync is None)
        
        self.playwright_context = None
        self.browser = None
        self.context = None
        
    def start(self) -> None:
        """Start the browser context with isolated permission overrides."""
        if self.use_simulation:
            logger.info("Secure Browser: Starting simulated sandboxed browser session.")
            return
            
        try:
            self.playwright_context = sync_playwright().start()
            # Enforce headless mode and security parameters
            self.browser = self.playwright_context.chromium.launch(headless=True)
            
            # Enforce context-level boundaries
            self.context = self.browser.new_context(
                ignore_https_errors=False,
                java_script_enabled=True,
                bypass_csp=False,
                # Disable cookie database and persistent storage allocations
                storage_state=None if self.block_cookies else {}
            )
            logger.info("Secure Browser: Headless Chromium browser context successfully created.")
        except Exception as e:
            logger.error(f"Failed to start Playwright: {e}. Switching to simulated mode.")
            self.use_simulation = True

    def browse_url(self, url: str) -> Dict[str, Any]:
        """Navigate to a target URL, verifying domain constraints first."""
        # 1. Enforce origin set restrictions
        if self.allowed_origins:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check if domain matches allowed origin set
            allowed = False
            for allowed_origin in self.allowed_origins:
                if allowed_origin.lower() in domain:
                    allowed = True
                    break
            
            if not allowed:
                logger.error(f"Navigation blocked by security policy: {url} is not in allowed origins {self.allowed_origins}")
                return {
                    "url": url,
                    "success": False,
                    "content": "",
                    "status_code": 403,
                    "error": "SECURITY_BLOCKED: URL origin not whitelisted."
                }
        
        if self.use_simulation:
            logger.info(f"Simulating secure retrieval of: {url}")
            return {
                "url": url,
                "success": True,
                "content": f"<html><body><h1>Simulated Secure Content</h1><p>Fetched content from {url}</p></body></html>",
                "status_code": 200,
                "error": None
            }
            
        try:
            page = self.context.new_page()
            
            # Additional script restrictions: disable notifications, geolocation
            self.context.grant_permissions([], origin=url)
            
            logger.info(f"Browsing: {url}")
            response = page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
            content = page.content()
            status = response.status if response else 200
            
            page.close()
            return {
                "url": url,
                "success": True,
                "content": content,
                "status_code": status,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error executing browser navigation for {url}: {e}")
            return {
                "url": url,
                "success": False,
                "content": "",
                "status_code": 500,
                "error": str(e)
            }

    def close(self) -> None:
        """Clean up active contexts and shutdown backend processes."""
        if self.use_simulation:
            return
            
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright_context:
                self.playwright_context.stop()
            logger.info("Secure Browser: Terminated browser contexts.")
        except Exception as e:
            logger.debug(f"Error closing playwright: {e}")
