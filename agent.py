import os
import json
import re
import dotenv
from datetime import datetime, timezone, timedelta

from meta_tools import MetaTools, meta_tool_functions
from utils import AgentUtils

from langchain_google_genai import ChatGoogleGenerativeAI

dotenv.load_dotenv()
current_date_and_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=4)))

# Start with only meta-tools to save tokens
initial_meta_functions = meta_tool_functions
initial_tool_signatures = AgentUtils.get_function_signatures(initial_meta_functions)

def create_system_prompt(interaction_memory, available_tools):
    memory_text = ""
    if interaction_memory:
        memory_text = f"""

Current interaction context:
{json.dumps(interaction_memory, indent=2)}
"""
    
    return f"""

You are a function calling AI model, that is the personal AI Agent of Mert. You must be proactive with your actions and reasoning. 

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

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.environ["GEMINI_API_KEY"], temperature=0.7, top_p=0.9, verbose=False)

# Conversation history
conversation_history = []

# Dynamic tool management
class ToolManager:
    def __init__(self):
        self.loaded_tools = {}
        self.available_functions = list(initial_meta_functions)
        self.available_signatures = initial_tool_signatures
    
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
        self.available_functions = list(initial_meta_functions)
        self.available_signatures = initial_tool_signatures

tool_manager = ToolManager()

def extract_tool_calls(text):
    """Extract tool calls from XML tags"""
    pattern = r'<tool_call>(.*?)</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]

while True:
    user_input = input("\nYou: ")
    
    # Reset interaction memory and tools for new user query
    current_interaction_memory = []
    tool_manager.reset_tools()
    
    # Create messages with current system prompt and conversation history
    system_prompt = create_system_prompt(current_interaction_memory, tool_manager.available_signatures)
    messages = [("system", system_prompt)] + conversation_history + [("human", user_input)]
    
    # Continue loop until agent returns non-tool response
    while True:
        response = model.invoke(messages)
        
        # Store agent response in interaction memory
        current_interaction_memory.append({
            "type": "agent_response",
            "content": response.content
        })
        
        # Check for tool calls
        tool_calls = extract_tool_calls(response.content)
        
        if not tool_calls:
            # No tool calls, final response
            print(f"\nAgent: {response.content}")
            break
        
        # Show intermediate text before tool calls
        text_before_tools = response.content.split('<tool_call>')[0].strip()
        if text_before_tools:
            print(f"\nAgent: {text_before_tools}")
        
        print(f"\n🔧 Found {len(tool_calls)} tool call(s)")
        
        # Execute all tool calls and collect results
        tool_results = []
        for i, tool_call in enumerate(tool_calls):
            # Check if this is a meta-tool call to load specific tools
            try:
                call_data = json.loads(tool_call)
                function_name = call_data.get('name', f'tool_call_{i+1}')
                print(f"\nExecuting {function_name}...")
                
                # Handle meta-tool calls specially
                if function_name.startswith('get_') and function_name.endswith('_tools'):
                    tool_category = function_name.replace('get_', '').replace('_tools', '')
                    result = tool_manager.load_tools(tool_category)
                    print(f"🔧 {result}")
                else:
                    result = AgentUtils.run_tool(tool_call, tool_manager.available_functions)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in tool call: {e}")
                print(f"Tool call content: {tool_call[:200]}...")
                result = f"Error: Invalid JSON format in tool call"
                function_name = f'invalid_tool_call_{i+1}'
            except Exception as e:
                print(f"❌ Error executing tool: {e}")
                result = f"Error: {str(e)}"
                function_name = f'error_tool_call_{i+1}'
            
            # Store tool call and result in interaction memory
            current_interaction_memory.append({
                "type": "tool_call",
                "function_name": function_name,
                "call": tool_call,
                "result": str(result)
            })
            
            tool_results.append(f"{function_name} result: {result}")
        
        # Add tool results to messages and update system prompt with interaction memory
        tool_results_text = "\n".join(tool_results)
        messages.append(("assistant", response.content))
        messages.append(("human", f"Tool results:\n{tool_results_text}"))
        
        # Update system prompt with current interaction memory and loaded tools
        system_prompt = create_system_prompt(current_interaction_memory, tool_manager.available_signatures)
        messages[0] = ("system", system_prompt)
    
    # Add final exchange to conversation history
    conversation_history.append(("human", user_input))
    conversation_history.append(("assistant", response.content))
    
    # Keep conversation history manageable (last 10 exchanges)
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    print(f"\nInput Tokens Used: {response.usage_metadata['input_tokens']}")
    print(f"Output Tokens Used: {response.usage_metadata['output_tokens']}")

