import requests
import json
import os
import pprint
from langchain_community.utilities import GoogleSerperAPIWrapper

class WebTools:
    '''Tools for the AI Agent regarding Google Web Search'''

    @staticmethod
    def perform_web_search(query: str) -> str:
        '''
        Perform Google web search and return results
        
        Args:
            query (str): Search query (e.g., "latest news about AI", "weather in Dubai")
        
        Returns:
            JSON string with search results including title, link, snippet for each result
        '''
        try:
            serper_api_key = os.getenv("SERPER_API_KEY")
            if not serper_api_key:
                return "Error: SERPER_API_KEY not found in environment variables. Please set it in your .env file."
            
            search = GoogleSerperAPIWrapper()
            results = search.run(query)
            return results
        except Exception as e:
            return f"Error performing web search: {str(e)}"
