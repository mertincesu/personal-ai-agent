from auth.google_auth import get_docs_service, get_drive_service
import os
import dotenv
import json
import re

dotenv.load_dotenv()

class DocsTools:
    '''Tools for AI Agent regarding Google Docs Service'''

    @staticmethod
    def create_google_docs_document(title: str, initial_content: str = "", format_as_markdown: bool = True) -> str:
        '''
        Create a new Google Docs document with optional formatted content
        
        Args:
            title (str): Title for the new document
            initial_content (str): Optional initial text content to add to the document (supports HTML/markdown formatting)
            format_as_markdown (bool): If True, convert markdown formatting to Google Docs formatting (default: True)
        
        Returns:
            JSON string with document ID, title, and web link
        '''
        try:
            docs_service = get_docs_service()
            
            # Create the document
            document = {
                'title': title
            }
            
            doc = docs_service.documents().create(body=document).execute()
            document_id = doc.get('documentId')
            
            # Add initial content if provided
            if initial_content:
                if format_as_markdown:
                    # Use the same markdown formatting logic as edit_google_docs_document
                    lines = initial_content.split('\n')
                    current_index = 1
                    requests = []
                    
                    for line in lines:
                        if not line.strip():
                            # Empty line
                            requests.append({
                                'insertText': {
                                    'location': {'index': current_index},
                                    'text': '\n'
                                }
                            })
                            current_index += 1
                            continue
                        
                        # Handle headers
                        if line.startswith('# '):
                            header_text = line[2:] + '\n'
                            requests.extend([
                                {
                                    'insertText': {
                                        'location': {'index': current_index},
                                        'text': header_text
                                    }
                                },
                                {
                                    'updateTextStyle': {
                                        'range': {
                                            'startIndex': current_index,
                                            'endIndex': current_index + len(header_text) - 1
                                        },
                                        'textStyle': {
                                            'bold': True,
                                            'fontSize': {'magnitude': 20, 'unit': 'PT'}
                                        },
                                        'fields': 'bold,fontSize'
                                    }
                                }
                            ])
                            current_index += len(header_text)
                        elif line.startswith('## '):
                            header_text = line[3:] + '\n'
                            requests.extend([
                                {
                                    'insertText': {
                                        'location': {'index': current_index},
                                        'text': header_text
                                    }
                                },
                                {
                                    'updateTextStyle': {
                                        'range': {
                                            'startIndex': current_index,
                                            'endIndex': current_index + len(header_text) - 1
                                        },
                                        'textStyle': {
                                            'bold': True,
                                            'fontSize': {'magnitude': 16, 'unit': 'PT'}
                                        },
                                        'fields': 'bold,fontSize'
                                    }
                                }
                            ])
                            current_index += len(header_text)
                        elif line.startswith('### '):
                            header_text = line[4:] + '\n'
                            requests.extend([
                                {
                                    'insertText': {
                                        'location': {'index': current_index},
                                        'text': header_text
                                    }
                                },
                                {
                                    'updateTextStyle': {
                                        'range': {
                                            'startIndex': current_index,
                                            'endIndex': current_index + len(header_text) - 1
                                        },
                                        'textStyle': {
                                            'bold': True,
                                            'fontSize': {'magnitude': 14, 'unit': 'PT'}
                                        },
                                        'fields': 'bold,fontSize'
                                    }
                                }
                            ])
                            current_index += len(header_text)
                        else:
                            # Regular text with potential bold formatting
                            processed_line = line + '\n'
                            
                            # Handle bold text (**text**)
                            bold_matches = list(re.finditer(r'\*\*(.*?)\*\*', processed_line))
                            for match in reversed(bold_matches):
                                start, end = match.span()
                                bold_text = match.group(1)
                                processed_line = processed_line[:start] + bold_text + processed_line[end:]
                            
                            requests.append({
                                'insertText': {
                                    'location': {'index': current_index},
                                    'text': processed_line
                                }
                            })
                            
                            # Apply bold formatting
                            for match in bold_matches:
                                start_pos = current_index + match.start() - (match.start() - len(match.group(1)))
                                end_pos = start_pos + len(match.group(1))
                                requests.append({
                                    'updateTextStyle': {
                                        'range': {
                                            'startIndex': start_pos,
                                            'endIndex': end_pos
                                        },
                                        'textStyle': {'bold': True},
                                        'fields': 'bold'
                                    }
                                })
                            
                            current_index += len(processed_line)
                else:
                    # Simple text insertion without formatting
                    requests = [
                        {
                            'insertText': {
                                'location': {'index': 1},
                                'text': initial_content
                            }
                        }
                    ]
                
                docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
            
            # Generate web view link
            web_view_link = f"https://docs.google.com/document/d/{document_id}/edit"
            
            return json.dumps({
                "status": "success",
                "document_id": document_id,
                "title": title,
                "web_view_link": web_view_link,
                "initial_content_added": bool(initial_content),
                "content_length": len(initial_content) if initial_content else 0
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to create document: {str(e)}"
            })

    @staticmethod
    def read_google_docs_document_contents(document_id: str) -> str:
        '''
        Read the contents of a Google Docs document
        
        Args:
            document_id (str): The ID of the Google Docs document (from URL or file listing)
        
        Returns:
            JSON string with document title and full text content
        '''
        try:
            docs_service = get_docs_service()
            
            # Get document
            document = docs_service.documents().get(documentId=document_id).execute()
            
            title = document.get('title', 'Untitled')
            content = document.get('body', {})
            
            # Extract text content
            text_content = ""
            if 'content' in content:
                for element in content['content']:
                    if 'paragraph' in element:
                        paragraph = element['paragraph']
                        if 'elements' in paragraph:
                            for elem in paragraph['elements']:
                                if 'textRun' in elem:
                                    text_content += elem['textRun'].get('content', '')
            
            return json.dumps({
                "status": "success",
                "document_id": document_id,
                "title": title,
                "content": text_content.strip(),
                "word_count": len(text_content.split())
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to read document: {str(e)}"
            })

    @staticmethod
    def list_google_docs_documents(max_results: int = 10) -> str:
        '''
        List Google Docs documents from Google Drive
        
        Args:
            max_results (int): Maximum number of documents to return (default: 10)
        
        Returns:
            JSON string with list of documents including ID, name, and last modified date
        '''
        try:
            drive_service = get_drive_service()
            
            # Query for Google Docs files
            results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.document'",
                pageSize=max_results,
                fields="files(id, name, modifiedTime, webViewLink, owners)"
            ).execute()
            
            files = results.get('files', [])
            
            documents = []
            for file in files:
                documents.append({
                    "id": file['id'],
                    "name": file['name'],
                    "modified_time": file.get('modifiedTime', ''),
                    "web_view_link": file.get('webViewLink', ''),
                    "owner": file.get('owners', [{}])[0].get('displayName', 'Unknown') if file.get('owners') else 'Unknown'
                })
            
            return json.dumps({
                "status": "success",
                "documents": documents,
                "count": len(documents)
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to list documents: {str(e)}"
            })

    @staticmethod
    def edit_google_docs_document(document_id: str, text_to_append: str, insert_at_beginning: bool = False, format_as_markdown: bool = True) -> str:
        '''
        Edit a Google Docs document by appending or prepending formatted text
        
        Args:
            document_id (str): The ID of the Google Docs document
            text_to_append (str): Text content to add to the document (supports HTML/markdown formatting: **bold**, # headers, ## subheaders, ### sub-subheaders)
            insert_at_beginning (bool): If True, insert at beginning; if False, append at end
            format_as_markdown (bool): If True, convert markdown formatting to Google Docs formatting (default: True)
        
        Returns:
            JSON string with operation status and document info
        '''
        try:
            docs_service = get_docs_service()
            
            # Get document to find insertion point
            document = docs_service.documents().get(documentId=document_id).execute()
            title = document.get('title', 'Untitled')
            
            # Find insertion point
            if insert_at_beginning:
                insert_index = 1
                text_content = text_to_append + '\n\n'
            else:
                # Find the actual end index
                body = document.get('body', {})
                end_index = 1  # Default to beginning if we can't determine end
                if 'content' in body and body['content']:
                    last_element = body['content'][-1]
                    if 'endIndex' in last_element:
                        end_index = last_element['endIndex'] - 1
                insert_index = end_index
                text_content = '\n\n' + text_to_append
            
            requests = []
            
            if format_as_markdown:
                # Parse markdown and create formatted requests
                lines = text_content.split('\n')
                current_index = insert_index
                
                for line in lines:
                    if not line.strip():
                        # Empty line
                        requests.append({
                            'insertText': {
                                'location': {'index': current_index},
                                'text': '\n'
                            }
                        })
                        current_index += 1
                        continue
                    
                    # Handle headers
                    if line.startswith('# '):
                        header_text = line[2:] + '\n'
                        requests.extend([
                            {
                                'insertText': {
                                    'location': {'index': current_index},
                                    'text': header_text
                                }
                            },
                            {
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': current_index,
                                        'endIndex': current_index + len(header_text) - 1
                                    },
                                    'textStyle': {
                                        'bold': True,
                                        'fontSize': {'magnitude': 20, 'unit': 'PT'}
                                    },
                                    'fields': 'bold,fontSize'
                                }
                            }
                        ])
                        current_index += len(header_text)
                    elif line.startswith('## '):
                        header_text = line[3:] + '\n'
                        requests.extend([
                            {
                                'insertText': {
                                    'location': {'index': current_index},
                                    'text': header_text
                                }
                            },
                            {
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': current_index,
                                        'endIndex': current_index + len(header_text) - 1
                                    },
                                    'textStyle': {
                                        'bold': True,
                                        'fontSize': {'magnitude': 16, 'unit': 'PT'}
                                    },
                                    'fields': 'bold,fontSize'
                                }
                            }
                        ])
                        current_index += len(header_text)
                    elif line.startswith('### '):
                        header_text = line[4:] + '\n'
                        requests.extend([
                            {
                                'insertText': {
                                    'location': {'index': current_index},
                                    'text': header_text
                                }
                            },
                            {
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': current_index,
                                        'endIndex': current_index + len(header_text) - 1
                                    },
                                    'textStyle': {
                                        'bold': True,
                                        'fontSize': {'magnitude': 14, 'unit': 'PT'}
                                    },
                                    'fields': 'bold,fontSize'
                                }
                            }
                        ])
                        current_index += len(header_text)
                    else:
                        # Regular text with potential bold/italic formatting
                        processed_line = line + '\n'
                        
                        # Handle bold text (**text**)
                        bold_matches = list(re.finditer(r'\*\*(.*?)\*\*', processed_line))
                        for match in reversed(bold_matches):  # Process in reverse to maintain indices
                            start, end = match.span()
                            bold_text = match.group(1)
                            processed_line = processed_line[:start] + bold_text + processed_line[end:]
                        
                        requests.append({
                            'insertText': {
                                'location': {'index': current_index},
                                'text': processed_line
                            }
                        })
                        
                        # Apply bold formatting
                        for match in bold_matches:
                            start_pos = current_index + match.start() - (match.start() - len(match.group(1)))
                            end_pos = start_pos + len(match.group(1))
                            requests.append({
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': start_pos,
                                        'endIndex': end_pos
                                    },
                                    'textStyle': {'bold': True},
                                    'fields': 'bold'
                                }
                            })
                        
                        current_index += len(processed_line)
            else:
                # Simple text insertion without formatting
                requests = [
                    {
                        'insertText': {
                            'location': {'index': insert_index},
                            'text': text_content
                        }
                    }
                ]
            
            # Execute the batch update
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            return json.dumps({
                "status": "success",
                "document_id": document_id,
                "document_title": title,
                "action": "inserted at beginning" if insert_at_beginning else "appended at end",
                "formatted": format_as_markdown,
                "text_added": text_to_append[:100] + "..." if len(text_to_append) > 100 else text_to_append
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to edit document: {str(e)}"
            })
