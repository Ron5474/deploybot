import os
import json
from langchain_core.tools import tool
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.environ["TAVILY_TOKEN"]

@tool
def web_search(query):
    """
    Search the web for information about self-hosted applications, setup guides, configuration help or any recent news. Use this for general questions that require up-to-date information
    """
    client = TavilyClient(api_key=TAVILY_API_KEY)

    response = client.search(query)
    results = response["results"]

    return json.dumps(results, indent=2)

