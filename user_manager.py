import os
import json
import boto3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import dotenv
import logging

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        """Initialize boto3 session and AWS resources"""
        # Create boto3 session with profile

        self.session = boto3.Session()
        # self.session = boto3.Session(profile_name="personal-aws")
        
        # Initialize AWS resources using the session
        self.dynamodb = self.session.resource('dynamodb')
        
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'ai-agent-dynamodb')
        self.table = self.dynamodb.Table(self.table_name)
        
    def get_conversation_history(self, email: str, limit: int = 10) -> List[Dict]:
        """
        Get conversation history for a user from DynamoDB
        
        Args:
            email: User email address
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of conversation messages sorted by timestamp (newest first)
        """
        try:
            response = self.table.get_item(
                Key={'user_email': email}
            )
            
            if 'Item' not in response:
                logger.info(f"No conversation history found for user {email}")
                return []
            
            item = response['Item']
            conversation_history = item.get('conversation_history', [])
            
            # Return the most recent messages (up to limit)
            recent_messages = conversation_history[-limit:] if len(conversation_history) > limit else conversation_history
            
            logger.info(f"Retrieved {len(recent_messages)} messages for user {email}")
            return recent_messages
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history for user {email}: {str(e)}")
            return []
    
    def update_conversation_history(self, email: str, message_type: str, content: str, 
                                  channel: str, thread_ts: str = None, tool_calls: List = None, 
                                  tokens_used: int = 0) -> bool:
        """
        Add a new message to conversation history in DynamoDB
        
        Args:
            email: User email address
            message_type: 'user' or 'assistant'
            content: Message content
            channel: Slack channel ID
            thread_ts: Thread timestamp (optional)
            tool_calls: List of tool calls made (optional)
            tokens_used: Number of tokens used (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            new_message = {
                'timestamp': timestamp,
                'message_type': message_type,
                'content': content,
                'channel': channel,
                'thread_ts': thread_ts or '',
                'tool_calls': tool_calls or [],
                'tokens_used': tokens_used
            }
            
            # Use UpdateExpression to append to the conversation_history list
            self.table.update_item(
                Key={'user_email': email},
                UpdateExpression='SET conversation_history = list_append(if_not_exists(conversation_history, :empty_list), :new_message)',
                ExpressionAttributeValues={
                    ':empty_list': [],
                    ':new_message': [new_message]
                }
            )
            
            logger.info(f"Added {message_type} message to conversation history for user {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating conversation history for user {email}: {str(e)}")
            return False
    
    def get_conversation_context(self, email: str, context_limit: int = 10) -> str:
        """
        Get recent conversation context formatted for AI model
        
        Args:
            email: User email address
            context_limit: Number of recent messages to include
            
        Returns:
            Formatted conversation context string
        """
        try:
            history = self.get_conversation_history(email, limit=context_limit)
            
            if not history:
                return ""
            
            context_lines = []
            context_lines.append("Recent conversation context:")
            
            # Reverse to show chronological order (oldest first)
            for msg in reversed(history):
                timestamp = msg['timestamp'][:19]  # Remove microseconds
                msg_type = msg['message_type'].upper()
                content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                
                context_lines.append(f"[{timestamp}] {msg_type}: {content}")
                
                if msg['tool_calls']:
                    tools = [call.get('function_name', 'unknown') for call in msg['tool_calls']]
                    context_lines.append(f"  Tools used: {', '.join(tools)}")
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Error getting conversation context for user {email}: {str(e)}")
            return ""
    
    def cleanup_old_conversations(self, email: str, keep_days: int = 30) -> bool:
        """
        Clean up old conversation history for a user by removing messages older than keep_days
        
        Args:
            email: User email address
            keep_days: Number of days to keep (default 30)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=keep_days)
            cutoff_timestamp = cutoff_date.isoformat()
            
            # Get current conversation history
            response = self.table.get_item(Key={'user_email': email})
            
            if 'Item' not in response:
                logger.info(f"No conversation history found for user {email}")
                return True
            
            conversation_history = response['Item'].get('conversation_history', [])
            
            # Filter out old messages
            filtered_history = [
                msg for msg in conversation_history 
                if msg.get('timestamp', '') >= cutoff_timestamp
            ]
            
            old_count = len(conversation_history) - len(filtered_history)
            
            if old_count > 0:
                # Update the conversation history with filtered messages
                self.table.update_item(
                    Key={'user_email': email},
                    UpdateExpression='SET conversation_history = :filtered_history',
                    ExpressionAttributeValues={
                        ':filtered_history': filtered_history
                    }
                )
                
                logger.info(f"Cleaned up {old_count} old messages for user {email}")
            else:
                logger.info(f"No old messages to clean up for user {email}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up old conversations for user {email}: {str(e)}")
            return False

# Global user manager instance
user_manager = UserManager()

def get_user_context(email: str) -> str:
    """Helper function to get user conversation context"""
    return user_manager.get_conversation_context(email)

def save_user_message(email: str, content: str, channel: str, thread_ts: str = None) -> bool:
    """Helper function to save user message"""
    return user_manager.update_conversation_history(
        email=email,
        message_type='user',
        content=content,
        channel=channel,
        thread_ts=thread_ts
    )

def save_assistant_message(email: str, content: str, channel: str, thread_ts: str = None, 
                         tool_calls: List = None, tokens_used: int = 0) -> bool:
    """Helper function to save assistant message"""
    return user_manager.update_conversation_history(
        email=email,
        message_type='assistant',
        content=content,
        channel=channel,
        thread_ts=thread_ts,
        tool_calls=tool_calls,
        tokens_used=tokens_used
    )
