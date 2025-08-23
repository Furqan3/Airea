"""Conversation management for AIREA Real Estate Chatbot."""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from models import ChatMessage, Client
from database import DatabaseManager
from ai_service import AIService

class ConversationManager:
    """Manages conversation state and flow."""
    
    def __init__(self, db_manager: DatabaseManager, ai_service: AIService):
        self.db_manager = db_manager
        self.ai_service = ai_service
        # In-memory conversation storage (consider Redis for production)
        self.active_conversations: Dict[str, List[ChatMessage]] = {}
        self.conversation_metadata: Dict[str, Dict[str, Any]] = {}
    
    def create_conversation(self) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        self.active_conversations[conversation_id] = []
        self.conversation_metadata[conversation_id] = {
            "created_at": datetime.now(),
            "stage": "welcome",
            "client_type": None,
            "extracted_clients": [],
            "processed": False
        }
        return conversation_id
    
    def add_message(self, conversation_id: str, message: ChatMessage) -> None:
        """Add a message to the conversation."""
        if conversation_id not in self.active_conversations:
            self.active_conversations[conversation_id] = []
        
        self.active_conversations[conversation_id].append(message)
        
        # Update conversation metadata
        if conversation_id in self.conversation_metadata:
            self.conversation_metadata[conversation_id]["updated_at"] = datetime.now()
    
    def get_conversation(self, conversation_id: str) -> Optional[List[ChatMessage]]:
        """Get conversation messages by ID."""
        return self.active_conversations.get(conversation_id)
    
    def get_conversation_metadata(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation metadata."""
        return self.conversation_metadata.get(conversation_id)
    
    def update_conversation_stage(self, conversation_id: str, stage: str) -> None:
        """Update the conversation stage."""
        if conversation_id in self.conversation_metadata:
            self.conversation_metadata[conversation_id]["stage"] = stage
    
    def analyze_conversation_progress(self, conversation_id: str) -> Dict[str, Any]:
        """Analyze conversation progress and determine next steps."""
        messages = self.get_conversation(conversation_id)
        if not messages:
            return {"error": "Conversation not found"}
        
        # Use AI service to analyze conversation stage
        analysis = self.ai_service.analyze_conversation_stage(messages)
        
        # Update metadata with analysis
        if conversation_id in self.conversation_metadata:
            self.conversation_metadata[conversation_id].update({
                "stage": analysis.get("stage", "unknown"),
                "analysis": analysis
            })
        
        return analysis
    
    def should_extract_data(self, conversation_id: str) -> bool:
        """Determine if conversation is ready for data extraction."""
        messages = self.get_conversation(conversation_id)
        metadata = self.get_conversation_metadata(conversation_id)
        
        if not messages or not metadata:
            return False
        
        # Don't extract if already processed
        if metadata.get("processed", False):
            return False
        
        # Extract if conversation has enough exchanges and contains essential contact info
        if len(messages) >= 8:  # Increased threshold for more complete conversations
            # Check if conversation contains essential information
            conversation_text = " ".join([msg.content.lower() for msg in messages])
            
            # Check for required fields
            has_email = "@" in conversation_text and "." in conversation_text
            has_phone = any(char.isdigit() for char in conversation_text) and len([c for c in conversation_text if c.isdigit()]) >= 10
            has_name = any(word in conversation_text for word in ["name", "i'm", "i am", "call me", "my name"])
            has_client_type = any(word in conversation_text for word in ["buy", "sell", "buyer", "seller", "buying", "selling"])
            
            # For sellers, check for address
            has_address = False
            if "sell" in conversation_text:
                has_address = any(word in conversation_text for word in ["address", "street", "road", "avenue", "drive", "lane", "boulevard"])
            
            # For buyers, check for area/preferences
            has_preferences = False
            if "buy" in conversation_text:
                has_preferences = any(word in conversation_text for word in ["area", "neighborhood", "budget", "price", "looking", "house", "apartment", "condo"])
            
            # Require all essential fields
            essential_complete = has_email and has_phone and has_name and has_client_type
            context_complete = has_address or has_preferences
            
            return essential_complete and context_complete
        
        return False
    
    def extract_and_process_clients(self, conversation_id: str) -> Dict[str, Any]:
        """Extract client data from conversation and process it."""
        messages = self.get_conversation(conversation_id)
        if not messages:
            return {"error": "Conversation not found", "success": False}
        
        try:
            # Extract client data using AI service
            extracted_clients = self.ai_service.extract_client_data(messages)
            
            if not extracted_clients:
                return {
                    "clients_extracted": 0,
                    "clients_processed": 0,
                    "success": False,
                    "errors": ["No client data could be extracted from the conversation"]
                }
            
            # Update conversation metadata
            if conversation_id in self.conversation_metadata:
                self.conversation_metadata[conversation_id]["extracted_clients"] = extracted_clients
                self.conversation_metadata[conversation_id]["processed"] = True
            
            # Save conversation to database
            self._save_conversation_to_db(conversation_id, messages, extracted_clients)
            
            return {
                "clients_extracted": len(extracted_clients),
                "clients_processed": len(extracted_clients),
                "success": True,
                "clients": extracted_clients
            }
            
        except Exception as e:
            error_msg = f"Error extracting client data: {str(e)}"
            print(error_msg)
            return {
                "clients_extracted": 0,
                "clients_processed": 0,
                "success": False,
                "errors": [error_msg]
            }
    
    def _save_conversation_to_db(self, conversation_id: str, messages: List[ChatMessage], clients: List[Client]) -> None:
        """Save conversation and client data to database."""
        try:
            # Convert messages to dict format for JSON storage
            messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            # Determine primary client email for conversation linking
            client_email = clients[0].email if clients else None
            
            # Save conversation
            self.db_manager.save_conversation(conversation_id, messages_dict, client_email)
            
            # Save interaction data for each client
            for client in clients:
                interaction_data = {
                    "conversation_id": conversation_id,
                    "messages": messages_dict,
                    "extracted_at": datetime.now().isoformat()
                }
                self.db_manager.save_interaction(client.email, str(interaction_data))
                
        except Exception as e:
            print(f"Error saving conversation to database: {e}")
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation."""
        messages = self.get_conversation(conversation_id)
        metadata = self.get_conversation_metadata(conversation_id)
        
        if not messages or not metadata:
            return {"error": "Conversation not found"}
        
        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "stage": metadata.get("stage", "unknown"),
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
            "processed": metadata.get("processed", False),
            "clients_extracted": len(metadata.get("extracted_clients", [])),
            "last_message": messages[-1] if messages else None
        }
    
    def list_active_conversations(self) -> List[Dict[str, Any]]:
        """List all active conversations with summaries."""
        summaries = []
        for conv_id in self.active_conversations.keys():
            summary = self.get_conversation_summary(conv_id)
            if "error" not in summary:
                summaries.append(summary)
        
        return sorted(summaries, key=lambda x: x.get("updated_at", x.get("created_at")), reverse=True)
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation from memory and database."""
        try:
            # Remove from memory
            if conversation_id in self.active_conversations:
                del self.active_conversations[conversation_id]
            if conversation_id in self.conversation_metadata:
                del self.conversation_metadata[conversation_id]
            
            # Remove from database
            return self.db_manager.delete_conversation(conversation_id)
            
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """Clean up old conversations from memory."""
        current_time = datetime.now()
        conversations_to_remove = []
        
        for conv_id, metadata in self.conversation_metadata.items():
            created_at = metadata.get("created_at", current_time)
            age_hours = (current_time - created_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                conversations_to_remove.append(conv_id)
        
        for conv_id in conversations_to_remove:
            if conv_id in self.active_conversations:
                del self.active_conversations[conv_id]
            if conv_id in self.conversation_metadata:
                del self.conversation_metadata[conv_id]
        
        return len(conversations_to_remove)