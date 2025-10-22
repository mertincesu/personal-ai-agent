import os
import json
import logging
import ssl
import certifi
import hashlib
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import dotenv
from utils import AgentUtils
from user_manager import get_user_context, save_user_message, save_assistant_message

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Global Slack client
slack_client = None

def init_slack_client(slack_bot_token: str):
    """Initialize the Slack client with the bot token"""
    global slack_client
    slack_client = WebClient(
        token=slack_bot_token,
        ssl=ssl.create_default_context(cafile=certifi.where())
    )

def _get_slack_client():
    """Get or create Slack client with token from environment"""
    global slack_client
    if slack_client is None:
        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            raise RuntimeError("Slack client not initialized. SLACK_BOT_TOKEN required.")
        init_slack_client(token)
    return slack_client


def post_message(channel, text, thread_ts=None):
    """Send a message to a Slack channel and return the message timestamp."""
    try:
        client = _get_slack_client()
        response = client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
        return response.get("ts")
    except SlackApiError as e:
        logger.error(f"SLACK_ERROR_POST_MESSAGE - channel={channel}, error={e.response['error']}")
        return None
    except Exception as e:
        logger.error(f"SLACK_ERROR_POST_MESSAGE - channel={channel}, error={str(e)}")
        return None

def start_typing(channel: str):
    """Start typing indicator in Slack channel"""
    try:
        # Note: conversations_typing API is not available in some Slack SDK versions
        # Commenting out for now
        # result = client.conversations_typing(channel=channel)
        # return result
        return None
    except SlackApiError as e:
        logger.error(f"SLACK_ERROR_START_TYPING - channel={channel}, error={e.response['error']}")
        return None
    except Exception as e:
        logger.error(f"SLACK_ERROR_START_TYPING - channel={channel}, error={str(e)}")
        return None

def format_for_slack(text: str) -> str:
    """Convert markdown formatting to Slack formatting"""
    # Convert **bold** to *bold* for Slack
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    return text

def get_user_email(user_id):
    """Get user email from Slack user ID."""
    try:
        client = _get_slack_client()
        response = client.users_info(user=user_id)
        user = response.get("user", {})
        profile = user.get("profile", {})
        email = profile.get("email", "")
        
        if not email:
            logger.warning(f"No email found for user {user_id}")
            return None
            
        logger.info(f"Retrieved email for user {user_id}: {email}")
        return email
        
    except SlackApiError as e:
        logger.error(f"SLACK_ERROR_GET_USER_EMAIL - user_id={user_id}, error={e.response['error']}")
        return None
    except Exception as e:
        logger.error(f"SLACK_ERROR_GET_USER_EMAIL - user_id={user_id}, error={str(e)}")
        return None

def update_message(channel, text, message_ts, thread_ts=None):
    """Update/edit an existing message in Slack."""
    try:
        client = _get_slack_client()
        result = client.chat_update(channel=channel, text=text, ts=message_ts)
        return result
    except SlackApiError as e:
        logger.error(f"SLACK_ERROR_UPDATE_MESSAGE - channel={channel}, message_ts={message_ts}, error={e.response['error']}")
        return post_message(channel, text, thread_ts)
    except Exception as e:
        logger.error(f"SLACK_ERROR_UPDATE_MESSAGE - channel={channel}, message_ts={message_ts}, error={str(e)}")
        return post_message(channel, text, thread_ts)


def stream_slack_response(channel: str, message_text: str, thread_ts: str = None, user_id: str = None):
    """Simple streaming response to Slack"""
    try:
        # Import server here to avoid circular import
        import server
        
        print(f"DEBUG: Streaming Slack response for channel {channel}, message_text {message_text}, thread_ts {thread_ts}, user_id {user_id}")

        print(f"DEBUG: Server components initialized")
        
        # 1. Get user email from Slack API
        user_email = None
        if user_id:
            user_email = get_user_email(user_id)
            if user_email:
                print(f"DEBUG: Retrieved email {user_email} for user {user_id}")
                # Save user message to conversation history
                save_user_message(user_email, message_text, channel, thread_ts)
            else:
                print(f"DEBUG: Could not retrieve email for user {user_id}")
        
        # 2. Start typing indicator
        start_typing(channel)
        print(f"DEBUG: Started typing indicator")
        
        # 3. Check if server components are initialized
        if not hasattr(server, 'tool_manager') or server.tool_manager is None:
            raise RuntimeError("Server not properly initialized - tool_manager is None")
        if not hasattr(server, 'model') or server.model is None:
            raise RuntimeError("Server not properly initialized - model is None")
        
        # 4. Reset and setup with conversation history
        server.tool_manager.reset_tools()
        current_interaction_memory = []
        
        # Get conversation context if we have user email
        conversation_context = ""
        if user_email:
            conversation_context = get_user_context(user_email)
            if conversation_context:
                print(f"DEBUG: Retrieved conversation context ({len(conversation_context)} chars)")
        
        system_prompt = server.create_system_prompt(current_interaction_memory, server.tool_manager.available_signatures)
        
        # Add conversation context to system prompt if available
        if conversation_context:
            system_prompt += f"\n\n{conversation_context}"
        
        messages = [("system", system_prompt), ("human", message_text)]
        
        tool_calls_made = []
        
        while True:
            print(f"DEBUG: Invoking model with message: {message_text[:50]}...")
            response = server.model.invoke(messages)
            print(f"DEBUG: Got response: {response.content[:100]}...")
            
            current_interaction_memory.append({"type": "agent_response", "content": response.content})
            
            tool_calls = server.extract_tool_calls(response.content)
            print(f"DEBUG: Found {len(tool_calls)} tool calls")
            
            if not tool_calls:
                # No more tool calls, post final response
                final_text = response.content
                
                # Add token usage info if available
                tokens_used = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    if hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                        input_tokens = usage.input_tokens
                        output_tokens = usage.output_tokens
                        tokens_used = input_tokens + output_tokens
                        final_text += f"\n\n[Tokens: {input_tokens} in, {output_tokens} out]"
                
                # Format for Slack (convert **bold** to *bold*)
                final_text = format_for_slack(final_text)
                
                post_message(channel, final_text, thread_ts)
                print(f"DEBUG: Posted final response")
                
                # Save assistant response to conversation history
                if user_email:
                    save_assistant_message(
                        user_email, 
                        final_text, 
                        channel, 
                        thread_ts, 
                        tool_calls_made, 
                        tokens_used
                    )
                    print(f"DEBUG: Saved assistant response to conversation history")
                
                break
            
            # Process tool calls
            for tool_call_str in tool_calls:
                try:
                    # Parse the JSON string to get the tool call object for tracking
                    tool_call = json.loads(tool_call_str)
                    function_name = tool_call.get("name", "unknown")
                    print(f"DEBUG: Processing tool call: {function_name}")
                    
                    # Track tool calls for saving to conversation history
                    tool_calls_made.append({
                        "function": function_name,
                        "arguments": tool_call.get("arguments", {})
                    })
                    
                    # Post tool execution message
                    post_message(channel, f"Executing {function_name}", thread_ts)
                    
                    # Handle meta-tool calls specially (same as server.py)
                    if function_name.startswith('get_') and function_name.endswith('_tools'):
                        tool_category = function_name.replace('get_', '').replace('_tools', '')
                        result = server.tool_manager.load_tools(tool_category)
                    else:
                        # Execute the tool - pass the original JSON string
                        result = AgentUtils.run_tool(tool_call_str, server.tool_manager.available_functions)
                    
                except json.JSONDecodeError as e:
                    print(f"DEBUG: Error parsing tool call JSON: {e}")
                    continue
                print(f"DEBUG: Tool result: {str(result)[:100]}...")
                
                current_interaction_memory.append({
                    "type": "tool_call",
                    "function": function_name,
                    "result": str(result)
                })
                
                # Update system prompt with new tools if any were loaded
                system_prompt = server.create_system_prompt(current_interaction_memory, server.tool_manager.available_signatures)
                
                # Add conversation context to updated system prompt if available
                if conversation_context:
                    system_prompt += f"\n\n{conversation_context}"
                
                messages = [("system", system_prompt), ("human", message_text)]
                
                # Add all previous responses to messages
                for memory in current_interaction_memory:
                    if memory["type"] == "agent_response":
                        messages.append(("assistant", memory["content"]))
                    elif memory["type"] == "tool_call":
                        messages.append(("human", f"Tool {memory['function']} returned: {memory['result']}"))
        
            messages[0] = ("system", system_prompt)
            
    except Exception as e:
        print(f"DEBUG: Exception in stream_slack_response: {str(e)}")
        error_msg = f"Error: {str(e)}"
        post_message(channel, error_msg, thread_ts)
