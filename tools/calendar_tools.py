from langchain.agents import tool
from auth.google_auth import get_calendar_service
import json
from datetime import datetime, timedelta

class CalendarTools:
    '''Calendar tools using our 3-key auth system'''

    @tool
    def get_calendar_events(date_range: str = "today") -> str:
        '''
        Get calendar events for specified date range
        
        Args:
            date_range (str): Date range options:
                - "today" (default) - today's events
                - "tomorrow" - tomorrow's events  
                - "week" - next 7 days
                - "YYYY-MM-DD" - specific date
        
        Returns:
            JSON string with calendar events
        '''
        try:
            service = get_calendar_service()
            
            # Calculate time range
            now = datetime.now()
            if date_range == "today":
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
            elif date_range == "tomorrow":
                start_time = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
            elif date_range == "week":
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=7)
            else:
                # Specific date
                try:
                    start_time = datetime.strptime(date_range, "%Y-%m-%d")
                    end_time = start_time + timedelta(days=1)
                except:
                    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_time = start_time + timedelta(days=1)
            
            # Convert to RFC3339 format
            time_min = start_time.isoformat() + 'Z'
            time_max = end_time.isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return json.dumps({
                    "status": "success",
                    "events": [],
                    "message": f"No events found for {date_range}",
                    "count": 0
                })
            
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                event_list.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                    'attendees': [att.get('email') for att in event.get('attendees', [])]
                })
            
            return json.dumps({
                "status": "success",
                "events": event_list,
                "count": len(event_list),
                "date_range": date_range
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to get calendar events: {str(e)}"
            })

    @tool
    def create_calendar_event(summary: str, start_datetime: str, end_datetime: str, location: str = "", description: str = "", attendees: str = "") -> str:
        '''
        Create a new calendar event (Dubai timezone)
        
        Args:
            summary (str): Event title/summary
            start_datetime (str): Start date and time "YYYY-MM-DD HH:MM:SS"
            end_datetime (str): End date and time "YYYY-MM-DD HH:MM:SS"
            location (str): Event location (optional)
            description (str): Event description (optional)
            attendees (str): Comma-separated email addresses (optional)
        
        Returns:
            JSON string with event creation status
        '''
        try:
            service = get_calendar_service()
            
            # Parse datetime strings and add Dubai timezone
            start_dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
            
            # Format for Google Calendar API
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
            
            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': 'Asia/Dubai',
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': 'Asia/Dubai',
                },
            }
            
            # Add attendees if provided
            if attendees:
                attendees_list = []
                for email in attendees.split(','):
                    attendees_list.append({'email': email.strip()})
                event['attendees'] = attendees_list
            
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            
            return json.dumps({
                "status": "success",
                "event_id": created_event.get('id'),
                "event_link": created_event.get('htmlLink'),
                "summary": summary,
                "start": start_datetime,
                "end": end_datetime
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to create event: {str(e)}"
            })

    @tool
    def search_calendar_events(query: str = "", start_date: str = "", end_date: str = "") -> str:
        '''
        Search calendar events
        
        Args:
            query (str): Search query text (optional)
            start_date (str): Start date "YYYY-MM-DD" (optional)
            end_date (str): End date "YYYY-MM-DD" (optional)
        
        Returns:
            JSON string with search results
        '''
        try:
            service = get_calendar_service()
            
            # Build search parameters
            search_params = {
                'calendarId': 'primary',
                'maxResults': 50,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if query:
                search_params['q'] = query
                
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    search_params['timeMin'] = start_dt.isoformat() + 'Z'
                except:
                    pass
                    
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    search_params['timeMax'] = end_dt.isoformat() + 'Z'
                except:
                    pass
            
            events_result = service.events().list(**search_params).execute()
            events = events_result.get('items', [])
            
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                event_list.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            return json.dumps({
                "status": "success",
                "events": event_list,
                "count": len(event_list),
                "query": query
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to search events: {str(e)}"
            })

    @tool
    def update_calendar_event(event_id: str, summary: str = "", start_datetime: str = "", end_datetime: str = "", location: str = "", description: str = "") -> str:
        '''
        Update an existing calendar event
        
        Args:
            event_id (str): Event ID to update
            summary (str): New title (optional)
            start_datetime (str): New start "YYYY-MM-DD HH:MM:SS" (optional)
            end_datetime (str): New end "YYYY-MM-DD HH:MM:SS" (optional)
            location (str): New location (optional)
            description (str): New description (optional)
        
        Returns:
            JSON string with update status
        '''
        try:
            service = get_calendar_service()
            
            # Get existing event
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update fields if provided
            if summary:
                event['summary'] = summary
            if location:
                event['location'] = location
            if description:
                event['description'] = description
                
            if start_datetime:
                start_dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
                event['start'] = {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Dubai'
                }
                
            if end_datetime:
                end_dt = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
                event['end'] = {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Dubai'
                }
            
            updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            
            return json.dumps({
                "status": "success",
                "event_id": event_id,
                "message": "Event updated successfully"
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to update event: {str(e)}"
            })

    @tool
    def delete_calendar_event(event_id: str) -> str:
        '''
        Delete a calendar event
        
        Args:
            event_id (str): Event ID to delete
        
        Returns:
            JSON string with deletion status
        '''
        try:
            service = get_calendar_service()
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            
            return json.dumps({
                "status": "success",
                "event_id": event_id,
                "message": "Event deleted successfully"
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to delete event: {str(e)}"
            })