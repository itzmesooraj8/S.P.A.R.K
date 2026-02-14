from spark.modules.tools import get_current_time, get_current_weather, search_wikipedia, get_news_headlines, get_stock_price, ask_wolframalpha

if __name__ == "__main__":
    print("Testing S.P.A.R.K. tools...")
    print("Current time:", get_current_time())
    print("Current weather:", get_current_weather("Kozhikode"))
    print("Wikipedia (Kozhikode):", search_wikipedia("Kozhikode"))
    print("Wikipedia (Python programming language):", search_wikipedia("Python (programming language)"))
    print("News headlines:", get_news_headlines())
    print("News headlines (AI):", get_news_headlines("artificial intelligence"))
    print("Stock price (AAPL):", get_stock_price("AAPL"))
    print("WolframAlpha (2+2):", ask_wolframalpha("2+2"))
    print("WolframAlpha (distance to moon):", ask_wolframalpha("distance to the moon"))
