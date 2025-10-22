from auth.google_auth import get_gmail_service
import json
import base64
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailTools:
    '''All the AI Agent tools related to Gmail'''

    @staticmethod
    def send_email(recipient_email_address: str, email_subject: str, email_content: str, content_type: str = "html") -> str:
        '''
        Send an email from mert.incesu03@gmail.com to the specified recipient
        
        Args:
            recipient_email_address (str): Valid email address (e.g., "user@example.com")
            email_subject (str): Email subject line
            email_content (str): Email body content (supports HTML/markdown formatting: **bold**, *italic*, # headers, ## subheaders, ### sub-subheaders)
            content_type (str): Content type - "html" for HTML content (default), you must use proper formatting, make important sections bold
        
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
                html_content = email_content
                
                # Convert markdown to HTML properly
                # Headers (must be at start of line)
                html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
                html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
                
                # Bold and italic (handle all instances)
                html_content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html_content)
                html_content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html_content)
                
                # Line breaks and paragraphs
                html_content = html_content.replace('\n\n', '</p><p>')
                html_content = html_content.replace('\n', '<br>')
                
                # Wrap in proper HTML with DOCTYPE
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 20px;">
    <div>
        <p>{html_content}</p>
    </div>
</body>
</html>"""
                
                
                # Add plain text version first
                plain_content = re.sub(r'<[^>]+>', '', email_content)
                plain_content = plain_content.replace('**', '').replace('*', '').replace('#', '')
                msg.attach(MIMEText(plain_content, 'plain'))
                
                # Add HTML version second (higher priority)
                msg.attach(MIMEText(html_content, 'html'))
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def reply_email(email_id: str, reply_content: str, content_type: str = "html") -> str:
        '''
        Reply to a specific email with your response using Gmail's proper reply mechanism
        
        Args:
            email_id (str): Email ID to reply to (from list_emails or search_emails)
            reply_content (str): Your reply message content (supports HTML/markdown formatting)
            content_type (str): Content type - "html" for HTML content (default), you must use proper formatting, make important sections bold
        
        Returns:
            JSON string with reply status, message_id, and confirmation details
        '''
        try:
            service = get_gmail_service()
            
            # Get original email
            original = service.users().messages().get(userId='me', id=email_id, format='full').execute()
            headers = original['payload'].get('headers', [])
            
            # Extract threading information
            original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
            original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            original_message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
            thread_id = original.get('threadId', '')
            
            # Process content
            if content_type == "html":
                html_content = reply_content
                html_content = html_content.replace('**', '<strong>').replace('**', '</strong>')
                html_content = html_content.replace('*', '<em>').replace('*', '</em>')
                html_content = html_content.replace('\n\n', '</p><p>')
                html_content = html_content.replace('\n', '<br>')
                
                if not html_content.startswith('<html>'):
                    html_content = f"<html><body><p>{html_content}</p></body></html>"
                
                final_content = html_content
            else:
                final_content = reply_content
            
            # Create proper reply using Gmail API
            reply_body = {
                'raw': base64.urlsafe_b64encode(
                    f"Content-Type: text/html; charset=utf-8\r\n"
                    f"MIME-Version: 1.0\r\n"
                    f"In-Reply-To: {original_message_id}\r\n"
                    f"References: {original_message_id}\r\n"
                    f"Subject: Re: {original_subject.replace('Re: ', '')}\r\n"
                    f"To: {original_from}\r\n"
                    f"From: mert.incesu03@gmail.com\r\n\r\n"
                    f"{final_content}".encode('utf-8')
                ).decode('utf-8'),
                'threadId': thread_id
            }
            
            # Send reply in thread
            result = service.users().messages().send(userId='me', body=reply_body).execute()
            
            return json.dumps({
                "status": "success",
                "reply_to": original_from,
                "thread_id": thread_id,
                "original_email_id": email_id,
                "reply_message_id": result.get('id', ''),
                "message": "Reply sent in thread successfully"
            })
        except Exception as e:
            return f'{{"status": "error", "message": "Failed to reply to email: {str(e)}"}}'

    @staticmethod
    def forward_email(email_id: str, recipient_email: str, forward_message: str = "", content_type: str = "html") -> str:
        '''
        Forward a specific email to another recipient using Gmail's proper forward mechanism
        
        Args:
            email_id (str): Email ID to forward (from list_emails or search_emails)
            recipient_email (str): Email address to forward to
            forward_message (str): Optional message to add before the forwarded content
            content_type (str): Content type - "html" for HTML content (default), you must use proper formatting, make important sections bold
        
        Returns:
            JSON string with forward status, message_id, and confirmation details
        '''
        try:
            service = get_gmail_service()
            
            # Get the original message in raw format to preserve all content
            original = service.users().messages().get(userId='me', id=email_id, format='raw').execute()
            original_raw = base64.urlsafe_b64decode(original['raw']).decode('utf-8')
            
            # Parse headers from raw message
            headers_end = original_raw.find('\r\n\r\n')
            if headers_end == -1:
                headers_end = original_raw.find('\n\n')
            
            original_headers = original_raw[:headers_end]
            original_body = original_raw[headers_end + 4:]
            
            # Extract subject from headers
            subject_match = None
            for line in original_headers.split('\n'):
                if line.lower().startswith('subject:'):
                    subject_match = line[8:].strip()
                    break
            
            original_subject = subject_match or "No Subject"
            forward_subject = f"Fwd: {original_subject}" if not original_subject.startswith('Fwd:') else original_subject
            
            # Process forward message
            if content_type == "html" and forward_message:
                processed_message = forward_message
                processed_message = processed_message.replace('**', '<strong>').replace('**', '</strong>')
                processed_message = processed_message.replace('*', '<em>').replace('*', '</em>')
                processed_message = processed_message.replace('\n\n', '</p><p>')
                processed_message = processed_message.replace('\n', '<br>')
                forward_message = f"<p>{processed_message}</p><br><br>"
            elif forward_message:
                forward_message = f"{forward_message}\n\n"
            
            # Create forward with original message embedded
            forward_raw = (
                f"Content-Type: text/html; charset=utf-8\r\n"
                f"MIME-Version: 1.0\r\n"
                f"Subject: {forward_subject}\r\n"
                f"To: {recipient_email}\r\n"
                f"From: mert.incesu03@gmail.com\r\n\r\n"
                f"{forward_message}"
                f"---------- Forwarded message ----------<br>"
                f"{original_raw.replace(chr(10), '<br>').replace(chr(13), '')}"
            )
            
            # Send forward
            forward_body = {
                'raw': base64.urlsafe_b64encode(forward_raw.encode('utf-8')).decode('utf-8')
            }
            
            result = service.users().messages().send(userId='me', body=forward_body).execute()
            
            return json.dumps({
                "status": "success",
                "forwarded_to": recipient_email,
                "subject": forward_subject,
                "original_email_id": email_id,
                "forward_message_id": result.get('id', ''),
                "message": "Email forwarded with original content successfully"
            })
        except Exception as e:
            return f'{{"status": "error", "message": "Failed to forward email: {str(e)}"}}'
