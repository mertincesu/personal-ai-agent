from langchain.agents import tool
from auth.google_auth import get_gmail_service
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailTools:
    '''All the AI Agent tools related to Gmail'''

    @tool
    def send_email(recipient_email_address: str, email_subject: str, email_content: str, content_type: str = "html") -> str:
        '''
        Send an email from mert.incesu03@gmail.com to the specified recipient
        
        Args:
            recipient_email_address (str): Valid email address (e.g., "user@example.com")
            email_subject (str): Email subject line
            email_content (str): Email body content (supports HTML/markdown formatting: **bold**, *italic*, # headers, ## subheaders, ### sub-subheaders)
            content_type (str): Content type - "html" for HTML content (default) or "plain" for plain text
        
        Returns:
            JSON string with send status, message_id, and confirmation details
        '''
        try:
            service = get_gmail_service()
            
            msg = MIMEMultipart('alternative')
            msg['From'] = "mert.incesu03@gmail.com"
            msg['To'] = recipient_email_address
            msg['Subject'] = email_subject
            
            # Convert markdown-style formatting to HTML if needed
            if content_type == "html":
                # Basic markdown to HTML conversion
                html_content = email_content
                html_content = html_content.replace('\n\n', '</p><p>')
                html_content = html_content.replace('\n', '<br>')
                html_content = html_content.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                html_content = html_content.replace('*', '<em>', 1).replace('*', '</em>', 1)
                html_content = html_content.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)
                html_content = html_content.replace('## ', '<h2>').replace('\n', '</h2>\n', 1)
                html_content = html_content.replace('### ', '<h3>').replace('\n', '</h3>\n', 1)
                
                # Wrap in proper HTML structure
                if not html_content.startswith('<html>'):
                    html_content = f"""
                    <html>
                        <body>
                            <p>{html_content}</p>
                        </body>
                    </html>
                    """
                
                msg.attach(MIMEText(html_content, 'html'))
                # Also attach plain text version
                plain_content = email_content.replace('**', '').replace('*', '').replace('#', '').replace('<br>', '\n')
                msg.attach(MIMEText(plain_content, 'plain'))
            else:
                msg.attach(MIMEText(email_content, 'plain'))
            
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            result = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            
            return json.dumps({
                "status": "success",
                "from": "mert.incesu03@gmail.com",
                "to": recipient_email_address,
                "subject": email_subject,
                "content_type": content_type,
                "message_id": result.get('id', ''),
                "message": "Email sent successfully"
            })
        except Exception as e:
            return f'{{"status": "error", "message": "Failed to send email: {str(e)}"}}'

    @tool
    def list_emails(folder: str = "INBOX", limit: int = 10) -> str:
        '''
        List recent emails from the specified folder
        
        Args:
            folder (str): Email folder name - one of:
                - "INBOX" (default) - inbox emails
                - "SENT" - sent emails
                - "DRAFTS" - draft emails
                - "SPAM" - spam folder
                - "TRASH" - deleted emails
            limit (int): Maximum number of emails to return (default: 10, max recommended: 50)
        
        Returns:
            JSON string with email list including email_id, from, subject, date, read_status
        '''
        try:
            service = get_gmail_service()
            
            label_map = {"INBOX": "INBOX", "SENT": "SENT", "DRAFTS": "DRAFT", "SPAM": "SPAM", "TRASH": "TRASH"}
            label_id = label_map.get(folder.upper(), folder)
            
            results = service.users().messages().list(userId='me', labelIds=[label_id], maxResults=limit).execute()
            emails = []
            
            for msg in results.get('messages', []):
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = message['payload'].get('headers', [])
                
                emails.append({
                    "email_id": msg['id'],
                    "from": next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender'),
                    "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                    "date": next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                    "read_status": "unread" if 'UNREAD' in message.get('labelIds', []) else "read"
                })
            
            return json.dumps({"status": "success", "emails": emails, "count": len(emails)})
        except Exception as e:
            return f'{{"status": "error", "message": "Failed to list emails: {str(e)}"}}'

    @tool
    def read_email(email_id: str, folder: str = "INBOX") -> str:
        '''
        Read complete email content and details for a specific email
        
        Args:
            email_id (str): Email ID from list_emails or search_emails (required)
            folder (str): Email folder name (default: "INBOX") - same options as list_emails
        
        Returns:
            JSON string with full email details including body_text, body_html, attachments, headers
        '''
        try:
            service = get_gmail_service()
            message = service.users().messages().get(userId='me', id=email_id, format='full').execute()
            
            headers = message['payload'].get('headers', [])
            body_text = ""
            body_html = ""
            attachments = []
            
            def extract_parts(payload):
                nonlocal body_text, body_html, attachments
                if 'parts' in payload:
                    for part in payload['parts']:
                        extract_parts(part)
                else:
                    mime_type = payload.get('mimeType', '')
                    filename = payload.get('filename', '')
                    
                    if filename:
                        attachments.append({
                            "filename": filename,
                            "content_type": mime_type,
                            "size": payload.get('body', {}).get('size', 0)
                        })
                    elif mime_type == 'text/plain' and payload.get('body', {}).get('data'):
                        body_text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                    elif mime_type == 'text/html' and payload.get('body', {}).get('data'):
                        body_html = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
            extract_parts(message['payload'])
            
            return json.dumps({
                "status": "success",
                "email_id": email_id,
                "from": next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender'),
                "to": next((h['value'] for h in headers if h['name'] == 'To'), ''),
                "cc": next((h['value'] for h in headers if h['name'] == 'Cc'), ''),
                "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                "date": next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                "body_text": body_text,
                "body_html": body_html,
                "attachments": attachments,
                "attachment_count": len(attachments)
            })
        except Exception as e:
            return f'{{"status": "error", "message": "Failed to read email: {str(e)}"}}'

    @tool
    def search_emails(query: str, folder: str = "INBOX", limit: int = 20) -> str:
        '''
        Search emails using query string in specified folder
        
        Args:
            query (str): Search query - can be:
                - Simple text (e.g., "meeting", "report") - searches subject and body
                - Gmail search operators (e.g., "from:user@example.com", "subject:meeting")
                - Combined queries (e.g., "from:boss@company.com meeting")
            folder (str): Email folder to search in (default: "INBOX") - same options as list_emails
            limit (int): Maximum number of results to return (default: 20, max recommended: 50)
        
        Returns:
            JSON string with matching emails including email_id, from, subject, date, snippet
        '''
        try:
            service = get_gmail_service()
            
            label_map = {"INBOX": "INBOX", "SENT": "SENT", "DRAFTS": "DRAFT", "SPAM": "SPAM", "TRASH": "TRASH"}
            label_id = label_map.get(folder.upper(), folder)
            search_query = f"in:{label_id.lower()} {query}"
            
            results = service.users().messages().list(userId='me', q=search_query, maxResults=limit).execute()
            emails = []
            
            for msg in results.get('messages', []):
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = message['payload'].get('headers', [])
                snippet = message.get('snippet', '')[:200]
                if len(snippet) == 200:
                    snippet += "..."
                
                emails.append({
                    "email_id": msg['id'],
                    "from": next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender'),
                    "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                    "date": next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                    "snippet": snippet
                })
            
            return json.dumps({"status": "success", "emails": emails, "count": len(emails), "query": query})
        except Exception as e:
            return f'{{"status": "error", "message": "Failed to search emails: {str(e)}"}}'
