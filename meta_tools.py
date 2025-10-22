"""
Meta-tools for dynamic tool loading to save tokens
"""

from tools.calendar_tools import CalendarTools
from tools.gmail_tools import GmailTools
from tools.contacts_tools import ContactsTools
from tools.docs_tools import DocsTools
from tools.web_tools import WebTools

from utils import AgentUtils

class MetaTools:
    
    @staticmethod
    def get_gmail_tools():
        """Get all Gmail-related tools for email management"""
        gmail_functions = [
            GmailTools.send_email,
            GmailTools.list_emails,
            GmailTools.read_email,
            GmailTools.search_emails,
            GmailTools.reply_email,
            GmailTools.forward_email,
        ]
        return {
            'functions': gmail_functions,
            'signatures': AgentUtils.get_function_signatures(gmail_functions),
            'category': 'gmail'
        }
    
    @staticmethod
    def get_calendar_tools():
        """Get all Calendar-related tools for calendar management"""
        calendar_functions = [
            CalendarTools.get_calendar_events,
            CalendarTools.create_calendar_event,
            CalendarTools.search_calendar_events,
            CalendarTools.update_calendar_event,
            CalendarTools.delete_calendar_event,
        ]
        return {
            'functions': calendar_functions,
            'signatures': AgentUtils.get_function_signatures(calendar_functions),
            'category': 'calendar'
        }
    
    @staticmethod
    def get_contacts_tools():
        """Get all Contacts-related tools for contact management"""
        contacts_functions = [
            ContactsTools.search_contacts_list,
            ContactsTools.list_all_contacts,
            ContactsTools.add_contact,
            ContactsTools.delete_contact,
            ContactsTools.edit_contact,
        ]
        return {
            'functions': contacts_functions,
            'signatures': AgentUtils.get_function_signatures(contacts_functions),
            'category': 'contacts'
        }
    
    @staticmethod
    def get_docs_tools():
        """Get all Google Docs-related tools for document management"""
        docs_functions = [
            DocsTools.create_google_docs_document,
            DocsTools.read_google_docs_document_contents,
            DocsTools.list_google_docs_documents,
            DocsTools.edit_google_docs_document,
        ]
        return {
            'functions': docs_functions,
            'signatures': AgentUtils.get_function_signatures(docs_functions),
            'category': 'docs'
        }
    
    @staticmethod
    def get_web_tools():
        """Get all Web-related tools for web search and browsing"""
        web_functions = [
            WebTools.perform_web_search
        ]
        return {
            'functions': web_functions,
            'signatures': AgentUtils.get_function_signatures(web_functions),
            'category': 'web'
        }
    


# Meta-tool functions that the agent can call
meta_tool_functions = [
    MetaTools.get_gmail_tools,
    MetaTools.get_calendar_tools,
    MetaTools.get_contacts_tools,
    MetaTools.get_docs_tools,
    MetaTools.get_web_tools,
]
