from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.callbacks import BaseCallbackHandler
import os
import dotenv

from datetime import datetime
current_datetime = datetime.now()

from tools.gmail_tools import GmailTools
from tools.web_tools import WebTools
from tools.docs_tools import DocsTools
from tools.calendar_tools import CalendarTools
from tools.contacts_tools import ContactsTools

dotenv.load_dotenv()

# Class Initializations
gmail_tools = GmailTools()
calendar_tools = CalendarTools()
web_tools = WebTools()
docs_tools = DocsTools()
contacts_tools = ContactsTools()

user_email = "mert.incesu.c@propertyfinder.ae"
user_name = "Mert Incesu"

prompt = ChatPromptTemplate.from_messages(
    [
        ("system",  "You are 'Viral', Mert Incesu's intelligent personal assistant. You are proactive, efficient, and minimize friction for Mert by automatically using available tools to complete tasks.\n\n"
                    "CORE BEHAVIOR:\n"
                    "- Always be proactive: When Mert mentions people, automatically search contacts to get their details\n"
                    "- When scheduling/calendar topics come up, automatically check his calendar for context\n"
                    "- When he asks to email someone, search contacts first, then send the email without asking for confirmation\n"
                    "- When he mentions meetings/calls, check his calendar to find relevant events\n"
                    "- Combine multiple tools intelligently to provide complete solutions\n"
                    "- Only ask for clarification when absolutely necessary - try to infer and act first\n\n"
                    "AVAILABLE TOOLS & WHEN TO USE THEM:\n"
                    "- Contacts: Search when people are mentioned by name, relationship (dad, mom, sister), or when emailing\n"
                    "- Calendar: Check when time/scheduling is discussed, or when confirming meeting details\n"
                    "- Email: Send when requested, using contact info you've found\n"
                    "- Docs: Create/edit when document work is needed\n"
                    "- Web: Search for information not available in other tools\n\n"
                    "SMART REASONING:\n"
                    "- If Mert says 'email dad', immediately search contacts for 'dad' relationship, then send email\n"
                    "- If he mentions 'tomorrow's meeting', check calendar for tomorrow's events\n"
                    "- If he says 'remind X about Y', search contacts for X, check calendar for Y, then email\n"
                    "- Always provide complete solutions, not partial ones\n\n"
                    "Mert's email: mert.incesu03@gmail.com\n"
                    f"Current date & time: {current_datetime}\n\n"
                    "Be helpful, efficient, and minimize back-and-forth. Act first, explain after."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY"), temperature=0.7, top_p=0.9)

tools = [gmail_tools.send_email, gmail_tools.list_emails, gmail_tools.search_emails, gmail_tools.read_email,  
        web_tools.perform_web_search, docs_tools.edit_google_docs_document, docs_tools.list_google_docs_documents, docs_tools.read_google_docs_document_contents,
        docs_tools.create_google_docs_document, calendar_tools.get_calendar_events, calendar_tools.create_calendar_event, calendar_tools.search_calendar_events, 
        calendar_tools.update_calendar_event, calendar_tools.delete_calendar_event,
        contacts_tools.list_all_contacts, contacts_tools.search_contacts_list, contacts_tools.edit_contact, contacts_tools.delete_contact, contacts_tools.add_contact]
agent = create_tool_calling_agent(model, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

conversation_history = []

class CustomCallback(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "Unknown Tool")
        print(f"Calling {tool_name}...")
    
    def on_tool_end(self, output, **kwargs):
        print("Tool completed")

def main():
    
    while True:
        user_input = input("\nYou: ")
        
        # Create callback handler
        callback = CustomCallback()
        
        agent_response = agent_executor.invoke(
            {
                "input": user_input,
                "chat_history": conversation_history
            },
            config={"callbacks": [callback]}
        )
        output = agent_response["output"]
        print(f"\nAgent: {output}")

        conversation_history.append(HumanMessage(content=user_input))
        conversation_history.append(AIMessage(content=output))

if __name__ == "__main__":
    main()


    