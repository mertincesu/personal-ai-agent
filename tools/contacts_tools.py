from langchain.agents import tool
import os
import json

class ContactsTools:
    '''AI Agent tools to access & search contacts (email, phone number, relation etc.)'''
    
    CONTACTS_FILE = os.path.join(os.path.dirname(__file__), 'contacts.json')

    @tool
    def search_contacts_list(query: str) -> str:
        '''Search contacts by name, email, phone, or relationship
        
        Args:
            query (str): Search term to find in contacts (name, email, phone, or relationship)
            
        Returns:
            JSON string with matching contacts or error message
        '''
        try:
            with open(ContactsTools.CONTACTS_FILE, 'r') as f:
                data = json.load(f)
            
            contacts = data.get('contacts', [])
            query_lower = query.lower()
            
            matching_contacts = []
            for contact in contacts:
                if (query_lower in contact.get('name', '').lower() or
                    query_lower in contact.get('email', '').lower() or
                    query_lower in contact.get('phone', '').lower() or
                    query_lower in contact.get('relationship', '').lower()):
                    matching_contacts.append(contact)
            
            return json.dumps({
                "status": "success",
                "query": query,
                "matches": matching_contacts,
                "count": len(matching_contacts)
            })
            
        except FileNotFoundError:
            return json.dumps({
                "status": "error",
                "message": "Contacts file not found"
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error searching contacts: {str(e)}"
            })

    @tool
    def list_all_contacts() -> str:
        '''List all contacts from the contacts.json file
        
        Returns:
            JSON string with all contacts or error message
        '''
        try:
            with open(ContactsTools.CONTACTS_FILE, 'r') as f:
                data = json.load(f)
            
            contacts = data.get('contacts', [])
            
            return json.dumps({
                "status": "success",
                "contacts": contacts,
                "count": len(contacts)
            })
            
        except FileNotFoundError:
            return json.dumps({
                "status": "error",
                "message": "Contacts file not found"
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error reading contacts: {str(e)}"
            })

    @tool
    def add_contact(name: str, email: str = "", phone: str = "", relationship: str = "") -> str:
        '''Add a new contact to the contacts.json file
        
        Args:
            name (str): Contact's full name
            email (str): Contact's email address (optional)
            phone (str): Contact's phone number (optional)
            relationship (str): Relationship to the contact (optional)
            
        Returns:
            JSON string with success status or error message
        '''
        try:
            # Read existing contacts
            try:
                with open(ContactsTools.CONTACTS_FILE, 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {"contacts": []}
            
            contacts = data.get('contacts', [])
            
            # Check if contact already exists
            for contact in contacts:
                if contact.get('name', '').lower() == name.lower():
                    return json.dumps({
                        "status": "error",
                        "message": f"Contact '{name}' already exists"
                    })
            
            # Add new contact
            new_contact = {
                "name": name,
                "email": email,
                "phone": phone,
                "relationship": relationship
            }
            
            contacts.append(new_contact)
            data['contacts'] = contacts
            
            # Save to file
            with open(ContactsTools.CONTACTS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            return json.dumps({
                "status": "success",
                "message": f"Contact '{name}' added successfully",
                "contact": new_contact
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error adding contact: {str(e)}"
            })

    @tool
    def delete_contact(name: str) -> str:
        '''Delete a contact from the contacts.json file
        
        Args:
            name (str): Name of the contact to delete
            
        Returns:
            JSON string with success status or error message
        '''
        try:
            with open(ContactsTools.CONTACTS_FILE, 'r') as f:
                data = json.load(f)
            
            contacts = data.get('contacts', [])
            original_count = len(contacts)
            
            # Remove contact with matching name
            contacts = [c for c in contacts if c.get('name', '').lower() != name.lower()]
            
            if len(contacts) == original_count:
                return json.dumps({
                    "status": "error",
                    "message": f"Contact '{name}' not found"
                })
            
            data['contacts'] = contacts
            
            # Save to file
            with open(ContactsTools.CONTACTS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            return json.dumps({
                "status": "success",
                "message": f"Contact '{name}' deleted successfully",
                "remaining_contacts": len(contacts)
            })
            
        except FileNotFoundError:
            return json.dumps({
                "status": "error",
                "message": "Contacts file not found"
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error deleting contact: {str(e)}"
            })

    @tool
    def edit_contact(name: str, new_name: str = "", new_email: str = "", new_phone: str = "", new_relationship: str = "") -> str:
        '''Edit an existing contact in the contacts.json file
        
        Args:
            name (str): Current name of the contact to edit
            new_name (str): New name for the contact (optional)
            new_email (str): New email for the contact (optional)
            new_phone (str): New phone for the contact (optional)
            new_relationship (str): New relationship for the contact (optional)
            
        Returns:
            JSON string with success status or error message
        '''
        try:
            with open(ContactsTools.CONTACTS_FILE, 'r') as f:
                data = json.load(f)
            
            contacts = data.get('contacts', [])
            contact_found = False
            
            # Find and update the contact
            for contact in contacts:
                if contact.get('name', '').lower() == name.lower():
                    contact_found = True
                    
                    # Update fields if new values provided
                    if new_name:
                        contact['name'] = new_name
                    if new_email:
                        contact['email'] = new_email
                    if new_phone:
                        contact['phone'] = new_phone
                    if new_relationship:
                        contact['relationship'] = new_relationship
                    
                    break
            
            if not contact_found:
                return json.dumps({
                    "status": "error",
                    "message": f"Contact '{name}' not found"
                })
            
            data['contacts'] = contacts
            
            # Save to file
            with open(ContactsTools.CONTACTS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            return json.dumps({
                "status": "success",
                "message": f"Contact '{name}' updated successfully",
                "updated_contact": contact
            })
            
        except FileNotFoundError:
            return json.dumps({
                "status": "error",
                "message": "Contacts file not found"
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error editing contact: {str(e)}"
            })