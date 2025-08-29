from langchain.agents import tool
import requests
import json
import os
import dotenv
import pprint
from langchain_community.utilities import GoogleSerperAPIWrapper

dotenv.load_dotenv()

class WebTools:
    '''Tools for the AI Agent regarding Google Web Search'''

    @tool
    def perform_web_search(query: str) -> str:
        '''
        Perform Google web search and return results
        
        Args:
            query (str): Search query (e.g., "latest news about AI", "weather in Dubai")
            num_results (int): Number of results to return (default: 5, max: 10)
        
        Returns:
            JSON string with search results including title, link, snippet for each result
        '''

        search = GoogleSerperAPIWrapper()
        results = search.run(query)

        return results
