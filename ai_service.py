"""AI service for AIREA Real Estate Chatbot."""

from typing import List, Union, Dict, Any
from google import genai
from google.genai import types
from models import Client, ChatMessage
from config import Config

class AIService:
    """Service for AI-powered chat and data extraction."""
    
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        try:
            with open("systempromt.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            # Default system prompt if file not found
            return """You are AIREA, a friendly and professional real estate assistant. 
            Help users with their property needs - buying, selling, or renting. 
            Collect essential information like name, contact details, property preferences, budget, and location.
            Be conversational and helpful while gathering the necessary information."""
    
    def generate_chat_response(self, input_data: Union[str, List[ChatMessage]]) -> str:
        """Generate AI response for user input."""
        try:
            # Convert input to string format for the AI
            if isinstance(input_data, list):
                # Format conversation history
                conversation_text = ""
                for message in input_data:
                    role = "User" if message.role == "user" else "Assistant"
                    conversation_text += f"{role}: {message.content}\n"
                input_text = conversation_text
            else:
                input_text = str(input_data)
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.7,
                    max_output_tokens=1000
                ),
                contents=input_text
            )
            
            return response.text
            
        except Exception as e:
            print(f"Error generating AI response: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
    
    def extract_client_data(self, conversation_data: Union[Dict, str, List[ChatMessage]]) -> List[Client]:
        """Extract client data from conversation."""
        try:
            # Format conversation for extraction
            if isinstance(conversation_data, list):
                # Convert ChatMessage objects to dict format
                formatted_conversation = []
                for message in conversation_data:
                    if isinstance(message, ChatMessage):
                        formatted_conversation.append({
                            "role": message.role,
                            "content": message.content
                        })
                    else:
                        formatted_conversation.append(message)
                conversation_text = str(formatted_conversation)
            else:
                conversation_text = str(conversation_data)
            
            extraction_prompt = f"""
Extract client information from this real estate conversation between AIREA and the user.

REQUIRED SCHEMA FIELDS:
- client_type: Must be either "Buyer" or "Seller" (REQUIRED)
- name: Client's full name (REQUIRED)
- phone: Phone number in format +1234567890 or 1234567890 (REQUIRED)
- email: Valid email address (REQUIRED)

OPTIONAL SCHEMA FIELDS:
- property_type: "House", "Apartment", "Condo", or "Townhouse"
- address: Property address or area of interest
- budget: Numeric value for budget (convert text like "$300k" to 300000)
- appointment: true/false if client wants an appointment
- appointment_time: ISO datetime if specific time mentioned
- details: Any additional notes or requirements

EXTRACTION RULES:
1. Only extract information explicitly stated by the user
2. For client_type: Determine from context if they're buying or selling
3. For phone: Clean format to digits only with optional + prefix
4. For email: Must be valid email format
5. For budget: Convert text amounts to numbers (e.g., "300k" → 300000, "$1.5M" → 1500000)
6. If required fields are missing, don't create a client record
7. Return empty array if no complete client data found

CONVERSATION:
{conversation_text}

Extract and return as JSON array of client objects following the exact schema.
"""
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=extraction_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": list[Client],
                }
            )
            
            if response.parsed:
                # Validate extracted data
                validated_clients = []
                for client_data in response.parsed:
                    try:
                        # Additional validation and cleaning
                        if hasattr(client_data, 'phone') and client_data.phone:
                            # Clean phone number
                            phone = ''.join(filter(str.isdigit, str(client_data.phone)))
                            if len(phone) == 10:
                                client_data.phone = phone
                            elif len(phone) == 11 and phone.startswith('1'):
                                client_data.phone = '+' + phone
                            else:
                                client_data.phone = '+' + phone if not phone.startswith('+') else phone
                        
                        # Validate the client object
                        validated_client = Client(**client_data.__dict__ if hasattr(client_data, '__dict__') else client_data)
                        validated_clients.append(validated_client)
                        
                    except Exception as validation_error:
                        print(f"Validation error for client data: {validation_error}")
                        continue
                
                return validated_clients
            else:
                print("No client data could be extracted from the conversation")
                return []
                
        except Exception as e:
            print(f"Error extracting client data: {e}")
            return []
    
    def analyze_conversation_stage(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Analyze the current stage of the conversation."""
        try:
            conversation_text = ""
            for message in messages:
                role = "User" if message.role == "user" else "Assistant"
                conversation_text += f"{role}: {message.content}\n"
            
            analysis_prompt = f"""
            Analyze this real estate conversation and determine:
            1. What stage is the conversation in? (welcome, needs_assessment, requirements_gathering, contact_info, appointment_scheduling, complete)
            2. What information has been collected so far?
            3. What information is still needed?
            4. Is the user ready for the next step?
            5. Any concerns or hesitations detected?
            
            Conversation:
            {conversation_text}
            
            Respond in JSON format with keys: stage, collected_info, missing_info, ready_for_next_step, concerns
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=analysis_prompt,
                config={
                    "response_mime_type": "application/json",
                }
            )
            
            if response.parsed:
                return response.parsed
            else:
                return {
                    "stage": "unknown",
                    "collected_info": [],
                    "missing_info": [],
                    "ready_for_next_step": True,
                    "concerns": []
                }
                
        except Exception as e:
            print(f"Error analyzing conversation stage: {e}")
            return {
                "stage": "unknown",
                "collected_info": [],
                "missing_info": [],
                "ready_for_next_step": True,
                "concerns": []
            }