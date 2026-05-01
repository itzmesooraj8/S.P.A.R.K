import logging
import json
from core.vector_store import SparkVectorMemory
from tools.web_search import get_stock_summary, _fetch
import urllib.parse
import re

logger = logging.getLogger("SPARK_PORTFOLIO")

class PortfolioTracker:
    def __init__(self, memory: SparkVectorMemory):
        self.memory = memory
        # We will use ChromaDB to store holding metadata.
        self.collection = memory.client.get_or_create_collection("spark_portfolio")

    def add_holding(self, symbol: str, quantity: float, buy_price: float):
        """Adds or updates a stock holding."""
        symbol = symbol.upper()
        # Check if already exists
        results = self.collection.get(ids=[symbol])
        if results and results['ids']:
            self.collection.delete(ids=[symbol])
            
        data = json.dumps({"quantity": quantity, "buy_price": buy_price})
        self.collection.add(
            documents=[data],
            metadatas=[{"type": "holding", "symbol": symbol}],
            ids=[symbol]
        )
        return f"I have added {quantity} shares of {symbol} at {buy_price} to your portfolio, sir."

    def remove_holding(self, symbol: str):
        symbol = symbol.upper()
        self.collection.delete(ids=[symbol])
        return f"I have removed {symbol} from your portfolio, sir."

    def get_portfolio_summary(self) -> str:
        """Calculates live P&L for all holdings."""
        results = self.collection.get(where={"type": "holding"})
        if not results or not results['ids']:
            return "Your portfolio is currently empty, sir."
            
        total_investment = 0.0
        total_current_value = 0.0
        
        briefing = []
        
        for i, symbol in enumerate(results['ids']):
            try:
                data = json.loads(results['documents'][i])
                qty = data["quantity"]
                buy_price = data["buy_price"]
                
                # Fetch live price
                query = symbol
                if not re.match(r"[\^.]", query) and len(query.split()) == 1:
                    query = query.upper() + ".NS"
                encoded = urllib.parse.quote(query)
                url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={encoded}"
                raw = _fetch(url)
                
                live_price = buy_price # Fallback
                if raw:
                    quote_data = json.loads(raw)
                    res = quote_data.get("quoteResponse", {}).get("result", [])
                    if res:
                        live_price = res[0].get("regularMarketPrice", buy_price)
                        
                investment = qty * buy_price
                current_val = qty * live_price
                total_investment += investment
                total_current_value += current_val
                
                pnl = current_val - investment
                pct = (pnl / investment) * 100 if investment else 0
                direction = "up" if pnl >= 0 else "down"
                
                briefing.append(f"{symbol} is {direction} {abs(pct):.1f}%")
                
            except Exception as e:
                logger.warning(f"Portfolio error for {symbol}: {e}")
                
        total_pnl = total_current_value - total_investment
        total_pct = (total_pnl / total_investment) * 100 if total_investment else 0
        overall_dir = "up" if total_pnl >= 0 else "down"
        
        summary = f"Your portfolio is overall {overall_dir} {abs(total_pct):.1f}%, sir. "
        summary += ". ".join(briefing) + "."
        return summary
