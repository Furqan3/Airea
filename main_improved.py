"""
AIREA Real Estate Chatbot API - Improved Version
AI-powered real estate assistant with lead management
"""

from fastapi import FastAPI, HTTPException, Depends, APIRouter, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import ValidationError
from typing import List, Dict, Any
from datetime import datetime
import json
import uvicorn
from pathlib import Path

# Import our modules
from config import Config
from models import (
    ChatRequest, ChatResponse, ConversationHistoryRequest, ProcessDataResponse,
    ClientResponse, ChatMessage, Client, ConversationListResponse, ConversationSummary
)
from database import DatabaseManager
from email_service import MailjetEmailService
from ai_service import AIService
from conversation_manager import ConversationManager

# Initialize FastAPI app
app = FastAPI(
    title=Config.API_TITLE,
    description=Config.API_DESCRIPTION,
    version=Config.API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_manager = DatabaseManager(Config.DATABASE_PATH)
email_service = MailjetEmailService(Config.EMAIL_CONFIG)
ai_service = AIService()
conversation_manager = ConversationManager(db_manager, ai_service)

# Validate configuration on startup
if not Config.validate_email_config():
    print("Warning: Email service not properly configured. Check your Mailjet credentials.")

def get_database():
    """Dependency to get database manager."""
    return db_manager

def get_email_service():
    """Dependency to get email service."""
    return email_service

def get_conversation_manager():
    """Dependency to get conversation manager."""
    return conversation_manager

def process_client_data(clients_list: List[Client], db: DatabaseManager, email_svc: MailjetEmailService) -> tuple[int, List[str]]:
    """Process extracted client data: save to DB and send emails."""
    processed_count = 0
    errors = []
    
    for client_data in clients_list:
        try:
            # Check if client is new and save to database
            is_new_client = db.save_client(client_data)
            
            if is_new_client:
                print(f"New client added: {client_data.name} ({client_data.email})")
                # Send welcome email to new client
                if email_svc.is_configured() and not email_svc.send_welcome_email(client_data):
                    errors.append(f"Failed to send welcome email to {client_data.email}")
            else:
                print(f"Existing client updated: {client_data.name} ({client_data.email})")
            
            # Send property details/appointment email
            if email_svc.is_configured() and not email_svc.send_property_details_email(client_data):
                errors.append(f"Failed to send property details email to {client_data.email}")
            
            # Notify agent
            if email_svc.is_configured() and not email_svc.send_agent_notification(client_data, is_new_client):
                errors.append(f"Failed to send agent notification for {client_data.email}")
            
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Error processing client {client_data.email}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    return processed_count, errors

# Create API Router
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "AIREA Real Estate Chatbot API",
        "version": Config.API_VERSION,
        "status": "operational"
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "services": {
            "database": "operational",
            "ai_service": "operational",
            "email_service": "operational" if email_service.is_configured() else "not_configured"
        }
    }

@api_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    conv_manager: ConversationManager = Depends(get_conversation_manager),
    db: DatabaseManager = Depends(get_database),
    email_svc: MailjetEmailService = Depends(get_email_service)
):
    """Main chat endpoint for conversing with the AI assistant."""
    try:
        # Generate conversation ID if not provided
        conv_id = request.conversation_id or conv_manager.create_conversation()
        
        # Add user message to conversation
        user_message = ChatMessage(role="user", content=request.message)
        conv_manager.add_message(conv_id, user_message)
        
        # Get conversation history for context
        conversation_history = conv_manager.get_conversation(conv_id)
        if not conversation_history:
            raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")
        
        # Generate AI response
        ai_response_text = ai_service.generate_chat_response(conversation_history)
        
        # Add AI response to conversation
        ai_message = ChatMessage(role="assistant", content=ai_response_text)
        conv_manager.add_message(conv_id, ai_message)
        
        # Check if we should automatically extract data
        clients_processed = None
        if conv_manager.should_extract_data(conv_id):
            # Process in background to avoid blocking the response
            background_tasks.add_task(
                auto_process_conversation,
                conv_id, conv_manager, db, email_svc
            )
        
        return ChatResponse(
            message=ai_response_text,
            conversation_id=conv_id,
            clients_processed=clients_processed
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

async def auto_process_conversation(
    conversation_id: str,
    conv_manager: ConversationManager,
    db: DatabaseManager,
    email_svc: MailjetEmailService
):
    """Background task to automatically process conversation data."""
    try:
        result = conv_manager.extract_and_process_clients(conversation_id)
        if result.get("success") and result.get("clients"):
            # Process clients (save to DB and send emails)
            processed_count, errors = process_client_data(result["clients"], db, email_svc)
            print(f"Auto-processed {processed_count} clients from conversation {conversation_id}")
            if errors:
                print(f"Errors during auto-processing: {errors}")
    except Exception as e:
        print(f"Error in auto-processing conversation {conversation_id}: {e}")

@api_router.post("/process-conversation", response_model=ProcessDataResponse)
async def process_conversation_endpoint(
    request: ConversationHistoryRequest,
    db: DatabaseManager = Depends(get_database),
    email_service: MailjetEmailService = Depends(get_email_service)
):
    """Process a complete conversation to extract and save client data."""
    try:
        # Extract client data from conversation
        clients_list = ai_service.extract_client_data(request.conversation_history)
        
        if not clients_list:
            return ProcessDataResponse(
                clients_extracted=0,
                clients_processed=0,
                success=True,
                errors=["No client data extracted from the conversation."]
            )
        
        clients_extracted = len(clients_list)
        
        # Process clients (save to DB and send emails)
        processed_count, errors = process_client_data(clients_list, db, email_service)
        
        # Save conversation history for each client
        for client_data in clients_list:
            try:
                interaction_data = {
                    "conversation": [msg.dict() for msg in request.conversation_history],
                    "processed_at": datetime.now().isoformat()
                }
                db.save_interaction(client_data.email, json.dumps(interaction_data))
            except Exception as e:
                errors.append(f"Error saving interaction for {client_data.email}: {str(e)}")
        
        return ProcessDataResponse(
            clients_extracted=clients_extracted,
            clients_processed=processed_count,
            success=processed_count > 0,
            errors=errors if errors else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing conversation: {str(e)}")

@api_router.post("/process-conversation/{conversation_id}", response_model=ProcessDataResponse)
async def process_conversation_by_id(
    conversation_id: str,
    conv_manager: ConversationManager = Depends(get_conversation_manager),
    db: DatabaseManager = Depends(get_database),
    email_service: MailjetEmailService = Depends(get_email_service)
):
    """Process a conversation by conversation ID."""
    try:
        result = conv_manager.extract_and_process_clients(conversation_id)
        
        if not result.get("success"):
            return ProcessDataResponse(
                clients_extracted=result.get("clients_extracted", 0),
                clients_processed=result.get("clients_processed", 0),
                success=False,
                errors=result.get("errors", ["Failed to extract client data"])
            )
        
        clients_list = result.get("clients", [])
        
        # Process clients (save to DB and send emails)
        processed_count, errors = process_client_data(clients_list, db, email_service)
        
        return ProcessDataResponse(
            clients_extracted=len(clients_list),
            clients_processed=processed_count,
            success=processed_count > 0,
            errors=errors if errors else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing conversation: {str(e)}")

@api_router.get("/clients", response_model=ClientResponse)
async def get_clients(db: DatabaseManager = Depends(get_database)):
    """Get all clients from the database."""
    try:
        clients_data = db.get_all_clients()
        
        # Convert database records to Client models
        clients = []
        for client_data in clients_data:
            # Convert appointment_time string back to datetime if exists
            if client_data.get('appointment_time'):
                try:
                    client_data['appointment_time'] = datetime.fromisoformat(client_data['appointment_time'])
                except ValueError:
                    client_data['appointment_time'] = None
            
            # Remove database-specific fields
            client_dict = {k: v for k, v in client_data.items() 
                          if k in Client.__fields__}
            
            try:
                client = Client(**client_dict)
                clients.append(client)
            except ValidationError as e:
                print(f"Error validating client data: {e}")
                continue
        
        return ClientResponse(
            clients=clients,
            total_count=len(clients)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving clients: {str(e)}")

@api_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get conversation history by ID."""
    try:
        messages = conv_manager.get_conversation(conversation_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        summary = conv_manager.get_conversation_summary(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "messages": [msg.dict() for msg in messages],
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")

@api_router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(conv_manager: ConversationManager = Depends(get_conversation_manager)):
    """List all active conversations."""
    try:
        summaries = conv_manager.list_active_conversations()
        
        conversation_summaries = []
        for summary in summaries:
            conv_summary = ConversationSummary(
                conversation_id=summary["conversation_id"],
                message_count=summary["message_count"],
                last_message=ChatMessage(**summary["last_message"]) if summary.get("last_message") else None
            )
            conversation_summaries.append(conv_summary)
        
        return ConversationListResponse(
            conversations=conversation_summaries,
            total_count=len(conversation_summaries)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")

@api_router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Delete a conversation."""
    try:
        success = conv_manager.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": f"Conversation {conversation_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

@api_router.get("/conversations/{conversation_id}/analysis")
async def analyze_conversation(
    conversation_id: str,
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Analyze conversation progress and stage."""
    try:
        analysis = conv_manager.analyze_conversation_progress(conversation_id)
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing conversation: {str(e)}")

@api_router.get("/email/test")
async def test_email(email_service: MailjetEmailService = Depends(get_email_service)):
    """Test email functionality."""
    if not email_service.is_configured():
        return {"error": "Mailjet client not initialized. Check your API credentials."}
    
    # Create a test client
    test_client = Client(
        client_type="Buyer",
        name="Test User",
        phone="+1234567890",
        email="test@example.com",
        property_type="House",
        budget=300000.0,
        details="This is a test email"
    )
    
    # Try to send test email
    success = email_service.send_welcome_email(test_client)
    
    return {
        "success": success,
        "message": "Test email sent" if success else "Failed to send test email",
        "configuration": {
            "sender_email": email_service.config['sender_email'],
            "agent_email": email_service.config['agent_email'],
            "api_configured": email_service.is_configured()
        }
    }

@api_router.post("/admin/cleanup-conversations")
async def cleanup_old_conversations(
    max_age_hours: int = 24,
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Admin endpoint to cleanup old conversations."""
    try:
        cleaned_count = conv_manager.cleanup_old_conversations(max_age_hours)
        return {
            "message": f"Cleaned up {cleaned_count} old conversations",
            "cleaned_count": cleaned_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up conversations: {str(e)}")

# Include API router
app.include_router(api_router)

# Frontend serving routes
frontend_path = Path(Config.FRONTEND_PATH)

# Serve static files (CSS, JS, images, etc.)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "_next/static")), name="static_files")
    app.mount("/_next", StaticFiles(directory=str(frontend_path / "_next")), name="next_files")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve Next.js frontend files."""
        # Handle specific files
        if path in ["favicon.ico", "robots.txt", "sitemap.xml"]:
            file_path = frontend_path / path
            if file_path.exists():
                return FileResponse(file_path)
        
        # Handle API routes (should not reach here due to router, but safety check)
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Handle specific HTML files
        if path.endswith(".html"):
            file_path = frontend_path / path
            if file_path.exists():
                return FileResponse(file_path, media_type="text/html")
        
        # Handle static files
        if "." in path.split("/")[-1]:  # File with extension
            file_path = frontend_path / path
            if file_path.exists():
                return FileResponse(file_path)
        
        # For all other routes, serve index.html (SPA routing)
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path, media_type="text/html")
        
        # Fallback
        raise HTTPException(status_code=404, detail="Page not found")

    @app.get("/")
    async def serve_index():
        """Serve the main index.html."""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path, media_type="text/html")
        return {"message": "AIREA Real Estate Chatbot API", "version": Config.API_VERSION, "note": "Frontend not found"}

else:
    @app.get("/")
    async def root_fallback():
        return {
            "message": "AIREA Real Estate Chatbot API", 
            "version": Config.API_VERSION,
            "note": "Frontend directory not found. Please ensure 'frontend/out' exists.",
            "api_docs": "/docs"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)