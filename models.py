"""Pydantic models for AIREA Real Estate Chatbot."""

from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional, Literal, List
from datetime import datetime

class Client(BaseModel):
    """Client data model."""
    client_type: Literal["Buyer", "Seller"] = Field(..., description="Whether the client is buying or selling")
    name: str = Field(..., min_length=1, description="Client's full name")
    phone: str = Field(..., pattern=r"^\+?\d{10,15}$", description="Client's phone number")
    email: EmailStr = Field(..., description="Client's email address")
    property_type: Optional[Literal["House", "Apartment", "Condo", "Townhouse"]] = Field(None, description="Type of property the client is interested in")
    address: Optional[str] = Field(None, min_length=1, description="Client's address")
    budget: Optional[float] = Field(None, ge=0, description="Client's budget for a property")
    appointment: Optional[bool] = Field(None, description="Whether the client is available for an appointment")
    appointment_time: Optional[datetime] = Field(None, description="Time for the appointment")
    details: Optional[str] = Field(None, min_length=1, description="Additional details about the client")

class ChatMessage(BaseModel):
    """Chat message model."""
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for continuity")

class ChatResponse(BaseModel):
    """Chat response model."""
    message: str = Field(..., description="AI response")
    conversation_id: str = Field(..., description="Conversation ID")
    clients_processed: Optional[int] = Field(None, description="Number of clients processed")

class ConversationHistoryRequest(BaseModel):
    """Conversation history request model."""
    conversation_history: List[ChatMessage] = Field(..., description="Complete conversation history")

class ProcessDataResponse(BaseModel):
    """Process data response model."""
    clients_extracted: int = Field(..., description="Number of clients extracted")
    clients_processed: int = Field(..., description="Number of clients successfully processed")
    success: bool = Field(..., description="Overall success status")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")

class ClientResponse(BaseModel):
    """Client response model."""
    clients: List[Client] = Field(..., description="List of clients")
    total_count: int = Field(..., description="Total number of clients")

class ConversationSummary(BaseModel):
    """Conversation summary model."""
    conversation_id: str = Field(..., description="Conversation ID")
    message_count: int = Field(..., description="Number of messages")
    last_message: Optional[ChatMessage] = Field(None, description="Last message in conversation")

class ConversationListResponse(BaseModel):
    """Conversation list response model."""
    conversations: List[ConversationSummary] = Field(..., description="List of conversations")
    total_count: int = Field(..., description="Total number of conversations")