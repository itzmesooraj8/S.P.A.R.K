import re
from spark.modules.brain import think_stream
from spark.modules.tools import get_current_time, get_current_weather, search_wikipedia, get_stock_price, ask_wolframalpha
from spark.modules.websearch import web_search
from spark.integrations.vector_db import PineconeMemory

async def orchestrate_conversation(user_input, location="Kozhikode"):
    """
    Orchestrates the conversation, using tools and personal memory if needed, and streams the response.
    """
    # Personal memory detection (RAG)
    if re.search(r"my notes|my document|my memory|my meeting|my summary|my pdf|personal|takeaway|from last week|from yesterday|from meeting|from document|from file|from report|from email", user_input, re.I):
        memory = PineconeMemory()
        memory_results = memory.retrieve(user_input)
        if memory_results:
            user_input = f"{user_input}\n(Personal memory: {' '.join(memory_results)})"

    # Tool use detection (simple pattern matching)
    if re.search(r"what.*time|current time|time now", user_input, re.I):
        tool_result = get_current_time()
        user_input = f"{user_input}\n(Real time: {tool_result})"
    elif re.search(r"weather|temperature|rain|forecast", user_input, re.I):
        tool_result = get_current_weather(location)
        user_input = f"{user_input}\n(Real weather: {tool_result})"
    elif re.search(r"search|google|web search|find|look up|lookup|online|internet", user_input, re.I):
        # Use web search for explicit search requests
        match = re.search(r"search (.+)|google (.+)|web search (.+)|find (.+)|look up (.+)|lookup (.+)|online (.+)|internet (.+)", user_input, re.I)
        topic = None
        if match:
            for group in match.groups():
                if group:
                    topic = group.strip(' ?.')
                    break
        if not topic:
            topic = user_input.strip(' ?.')
        tool_result = web_search(topic)
        user_input = f"{user_input}\n(Web search: {tool_result})"
    elif re.search(r"wikipedia|who is|what is|tell me about|define|summary|explain|history of|where is|when was|how does", user_input, re.I):
        # Try to extract the topic for Wikipedia search
        match = re.search(r"wikipedia (.+)|who is (.+)|what is (.+)|tell me about (.+)|define (.+)|summary of (.+)|explain (.+)|history of (.+)|where is (.+)|when was (.+)|how does (.+)", user_input, re.I)
        topic = None
        if match:
            for group in match.groups():
                if group:
                    topic = group.strip(' ?.')
                    break
        if not topic:
            topic = user_input.strip(' ?.')
        tool_result = search_wikipedia(topic)
        user_input = f"{user_input}\n(Wikipedia: {tool_result})"
    elif re.search(r"stock|share price|market price|quote", user_input, re.I):
        # Stock price
        match = re.search(r"stock (.+)|share price (.+)|market price (.+)|quote (.+)", user_input, re.I)
        symbol = None
        if match:
            for group in match.groups():
                if group:
                    symbol = group.strip(' ?.')
                    break
        if not symbol:
            symbol = user_input.strip(' ?.')
        tool_result = get_stock_price(symbol)
        user_input = f"{user_input}\n(Stock: {tool_result})"
    elif re.search(r"calculate|math|solve|compute|wolfram|how much|how many|what is the result|answer to", user_input, re.I):
        # WolframAlpha
        match = re.search(r"calculate (.+)|math (.+)|solve (.+)|compute (.+)|wolfram (.+)|how much (.+)|how many (.+)|what is the result (.+)|answer to (.+)", user_input, re.I)
        query = None
        if match:
            for group in match.groups():
                if group:
                    query = group.strip(' ?.')
                    break
        if not query:
            query = user_input.strip(' ?.')
        tool_result = ask_wolframalpha(query)
        user_input = f"{user_input}\n(WolframAlpha: {tool_result})"

    # Stream the brain's response
    async for chunk in think_stream(user_input):
        yield chunk
