from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import json
import re
import dotenv
import hashlib
from datetime import datetime, timezone, timedelta
from slack import stream_slack_response

from meta_tools import MetaTools, meta_tool_functions
from utils import AgentUtils
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
dotenv.load_dotenv()

# Global variables for agent components
model = None
tool_manager = None
current_date_and_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=4)))

# Dynamic tool management
class ToolManager:
    def __init__(self):
        self.loaded_tools = {}
        self.available_functions = list(meta_tool_functions)
        self.available_signatures = AgentUtils.get_function_signatures(meta_tool_functions)
    
    def load_tools(self, tool_category):
        """Load tools for a specific category"""
        if tool_category not in self.loaded_tools:
            meta_tool_map = {
                'gmail': MetaTools.get_gmail_tools,
                'calendar': MetaTools.get_calendar_tools,
                'contacts': MetaTools.get_contacts_tools,
                'docs': MetaTools.get_docs_tools,
                'web': MetaTools.get_web_tools
            }
            
            if tool_category in meta_tool_map:
                tool_data = meta_tool_map[tool_category]()
                self.loaded_tools[tool_category] = tool_data
                self.available_functions.extend(tool_data['functions'])
                self.available_signatures += "\n\n" + tool_data['signatures']
                return f"Loaded {tool_category} tools successfully"
            else:
                return f"Unknown tool category: {tool_category}"
        else:
            return f"{tool_category} tools already loaded"
    
    def reset_tools(self):
        """Reset to only meta-tools for new interaction"""
        self.loaded_tools = {}
        self.available_functions = list(meta_tool_functions)
        self.available_signatures = AgentUtils.get_function_signatures(meta_tool_functions)

# Initialize components after class definition
print("INFO: Initializing AI Agent components...")
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=os.environ["GEMINI_API_KEY"], 
    temperature=0.7, 
    top_p=0.9, 
    verbose=False
)
tool_manager = ToolManager()
print("SUCCESS: AI Agent components initialized!")

def create_system_prompt(interaction_memory, available_tools):
    memory_text = ""
    if interaction_memory:
        memory_text = f"""

Current interaction context:
{json.dumps(interaction_memory, indent=2)}
"""
    
    return f"""

You are a function calling AI model, that is the personal AI Agent of Mert. You must be proactive. 

Mert's email address is mert.incesu03@gmail.com

You are provided with function signatures within <tools></tools> XML tags.
You may call one or more functions to assist with the user query. Don't make assumptions about what values to plug
into functions. Pay special attention to the properties 'types'. You should use those types as in a Python dict.
For each function call return a json object with function name and arguments within <tool_call></tool_call>
XML tags as follows:

<tool_call>
{{"name": <function-name>,"arguments": <args-dict>,  "id": <monotonically-increasing-id>}}
</tool_call>

IMPORTANT: If you need to perform actions like sending emails, managing calendar, contacts, documents, or web search,
you must first call the appropriate get_*_tools function (e.g., get_gmail_tools, get_calendar_tools) to load the specific tools you need.

Today's Date and Time: {current_date_and_time}

Here are the available tools:

<tools>
{available_tools}
</tools>
{memory_text}
"""

def extract_tool_calls(text):
    """Extract tool calls from XML tags"""
    pattern = r'<tool_call>(.*?)</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("INFO_1:Initializing AI Agent...")
    
    # Components already initialized on import
    print("SUCCESS_1: AI Agent initialized successfully!")
    yield
    # Shutdown
    print("🛑 Shutting down AI Agent...")

app = FastAPI(title="Mert's AI Agent API", lifespan=lifespan)


@app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack Events API requests"""
    try:
        body = await request.json()
        
        # URL verification
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # Event callbacks
        if body.get("type") == "event_callback":
            event = body.get("event", {})
            
            # Skip bot messages
            if event.get("bot_id"):
                return {"status": "ok"}
            
            # Handle messages and mentions - PREVENT DUPLICATES
            if event.get("type") in ["message", "app_mention"] and "subtype" not in event:
                # Check if we already processed this event
                event_ts = event.get("ts", "")
                event_channel = event.get("channel", "")
                event_user = event.get("user", "")
                event_text = event.get("text", "")
                
                # Create more robust event ID including text hash for better deduplication
                text_hash = hashlib.md5(event_text.encode()).hexdigest()[:8]
                event_id = f"{event_ts}_{event_channel}_{event_user}_{text_hash}"
                
                # Simple in-memory deduplication (you can use Redis for production)
                if not hasattr(slack_events, '_processed_events'):
                    slack_events._processed_events = set()
                
                if event_id in slack_events._processed_events:
                    print(f"DEBUG: Duplicate event detected and skipped: {event_id}")
                    return {"status": "ok"}
                
                slack_events._processed_events.add(event_id)
                print(f"DEBUG: Processing new event: {event_id}")
                
                # Keep only last 1000 events to prevent memory leak
                if len(slack_events._processed_events) > 1000:
                    slack_events._processed_events = set(list(slack_events._processed_events)[-500:])
                
                message_text = event.get("text", "")
                
                # Remove mention for app_mention events
                if event.get("type") == "app_mention":
                    message_text = message_text.split('>', 1)[-1].strip()
                
                if message_text:
                    print(f"DEBUG: Calling stream_slack_response")
                    stream_slack_response(event.get("channel"), message_text, event.get("thread_ts"), event.get("user"))
        
        return {"status": "ok"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Mert's AI Agent API is running!", "status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
