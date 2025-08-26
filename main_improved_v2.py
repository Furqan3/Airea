"""
AIREA Real Estate Chatbot API - Enhanced Version with Manual Processing
AI-powered real estate assistant with improved lead management and email logging
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

def process_client_data_enhanced(clients_list: List[Client], db: DatabaseManager, email_svc: MailjetEmailService, processing_method: str = "Manual") -> tuple[int, List[str], List[dict]]:
    """Process extracted client data: save to DB and send emails with detailed logging."""
    processed_count = 0
    errors = []
    email_results = []
    
    print(f"\n🚀 STARTING CLIENT DATA PROCESSING")
    print(f"📊 Processing Method: {processing_method}")
    print(f"👥 Clients to Process: {len(clients_list)}")
    print("="*70)
    
    for i, client_data in enumerate(clients_list, 1):
        try:
            print(f"\n👤 PROCESSING CLIENT {i}/{len(clients_list)}: {client_data.name}")
            print(f"📧 Email: {client_data.email}")
            print(f"📱 Phone: {client_data.phone}")
            print(f"🏠 Type: {client_data.client_type}")
            
            # Check if client is new and save to database
            is_new_client = db.save_client(client_data)
            
            if is_new_client:
                print(f"✅ NEW CLIENT ADDED to database")
            else:
                print(f"🔄 EXISTING CLIENT UPDATED in database")
            
            # Use the enhanced email processing function
            if email_svc.is_configured():
                email_result = email_svc.send_manual_lead_processing_email(
                    client_data, is_new_client, processing_method
                )
                email_results.append(email_result)
                
                # Add any email errors to the main errors list
                if email_result.get("errors"):
                    errors.extend(email_result["errors"])
                
                if email_result.get("success"):
                    print(f"✅ ALL EMAILS SENT SUCCESSFULLY for {client_data.name}")
                else:
                    print(f"❌ SOME EMAILS FAILED for {client_data.name}")
            else:
                print(f"⚠️  EMAIL SERVICE NOT CONFIGURED - Skipping emails")
                errors.append("Email service not configured")
            
            processed_count += 1
            print(f"✅ CLIENT {i} PROCESSING COMPLETE")
            
        except Exception as e:
            error_msg = f"Error processing client {client_data.email}: {e}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
    
    print(f"\n📊 PROCESSING SUMMARY:")
    print(f"   ✅ Clients Processed: {processed_count}/{len(clients_list)}")
    print(f"   📧 Email Results: {len(email_results)} sets sent")
    print(f"   ❌ Total Errors: {len(errors)}")
    if errors:
        print(f"   📝 Error Details:")
        for error in errors:
            print(f"      - {error}")
    print("="*70)
    
    return processed_count, errors, email_results

# Create API Router
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "AIREA Real Estate Chatbot API - Enhanced Version",
        "version": Config.API_VERSION,
        "status": "operational",
        "features": {
            "manual_processing": True,
            "detailed_email_logging": True,
            "enhanced_function_calls": True
        }
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
    conv_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Main chat endpoint for conversing with the AI assistant - NO AUTOMATIC PROCESSING."""
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
        
        # NO AUTOMATIC PROCESSING - Manual only via function calls
        print(f"💬 Chat response generated for conversation {conv_id}")
        print(f"📊 Message count: {len(conversation_history) + 1}")
        print(f"🔧 Use /api/process-conversation/{conv_id} for manual processing")
        
        return ChatResponse(
            message=ai_response_text,
            conversation_id=conv_id,
            clients_processed=None
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@api_router.post("/process-conversation", response_model=ProcessDataResponse)
async def process_conversation_endpoint(
    request: ConversationHistoryRequest,
    db: DatabaseManager = Depends(get_database),
    email_service: MailjetEmailService = Depends(get_email_service)
):
    """MANUAL PROCESSING: Process a complete conversation to extract and save client data."""
    try:
        print(f"\n🔧 MANUAL CONVERSATION PROCESSING INITIATED")
        print(f"📊 Conversation Messages: {len(request.conversation_history)}")
        
        # Extract client data from conversation
        clients_list = ai_service.extract_client_data(request.conversation_history)
        
        if not clients_list:
            print("⚠️  No client data extracted from conversation")
            return ProcessDataResponse(
                clients_extracted=0,
                clients_processed=0,
                success=True,
                errors=["No client data extracted from the conversation."]
            )
        
        clients_extracted = len(clients_list)
        print(f"✅ Extracted {clients_extracted} clients from conversation")
        
        # Process clients with enhanced logging
        processed_count, errors, email_results = process_client_data_enhanced(
            clients_list, db, email_service, "Manual API Call"
        )
        
        # Save conversation history for each client
        for client_data in clients_list:
            try:
                interaction_data = {
                    "conversation": [msg.dict() for msg in request.conversation_history],
                    "processed_at": datetime.now().isoformat(),
                    "processing_method": "Manual API Call"
                }
                db.save_interaction(client_data.email, json.dumps(interaction_data))
                print(f"💾 Saved interaction history for {client_data.email}")
            except Exception as e:
                error_msg = f"Error saving interaction for {client_data.email}: {str(e)}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return ProcessDataResponse(
            clients_extracted=clients_extracted,
            clients_processed=processed_count,
            success=processed_count > 0,
            errors=errors if errors else None
        )
        
    except Exception as e:
        print(f"❌ Error in manual processing: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing conversation: {str(e)}")

@api_router.post("/process-conversation/{conversation_id}", response_model=ProcessDataResponse)
async def process_conversation_by_id(
    conversation_id: str,
    conv_manager: ConversationManager = Depends(get_conversation_manager),
    db: DatabaseManager = Depends(get_database),
    email_service: MailjetEmailService = Depends(get_email_service)
):
    """MANUAL PROCESSING: Process a conversation by conversation ID with enhanced logging."""
    try:
        print(f"\n🔧 MANUAL PROCESSING BY CONVERSATION ID: {conversation_id}")
        
        result = conv_manager.extract_and_process_clients(conversation_id)
        
        if not result.get("success"):
            print(f"❌ Failed to extract client data from conversation {conversation_id}")
            return ProcessDataResponse(
                clients_extracted=result.get("clients_extracted", 0),
                clients_processed=result.get("clients_processed", 0),
                success=False,
                errors=result.get("errors", ["Failed to extract client data"])
            )
        
        clients_list = result.get("clients", [])
        print(f"✅ Extracted {len(clients_list)} clients from conversation {conversation_id}")
        
        # Process clients with enhanced logging
        processed_count, errors, email_results = process_client_data_enhanced(
            clients_list, db, email_service, f"Manual Processing (Conv: {conversation_id})"
        )
        
        return ProcessDataResponse(
            clients_extracted=len(clients_list),
            clients_processed=processed_count,
            success=processed_count > 0,
            errors=errors if errors else None
        )
        
    except Exception as e:
        print(f"❌ Error processing conversation {conversation_id}: {e}")
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
    """Test email functionality with detailed logging."""
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
        details="This is a test email from the enhanced AIREA system"
    )
    
    print(f"\n🧪 TESTING EMAIL FUNCTIONALITY")
    
    # Try to send test emails with detailed logging
    email_results = email_service.send_manual_lead_processing_email(
        test_client, True, "Email Test"
    )
    
    return {
        "success": email_results.get("success", False),
        "message": "Test emails processed" if email_results.get("success") else "Some test emails failed",
        "detailed_results": email_results,
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
        return {"message": "AIREA Real Estate Chatbot API - Enhanced", "version": Config.API_VERSION, "note": "Frontend not found"}

else:
    @app.get("/")
    async def root_fallback():
        return {
            "message": "AIREA Real Estate Chatbot API - Enhanced Version", 
            "version": Config.API_VERSION,
            "note": "Frontend directory not found. Please ensure 'frontend/out' exists.",
            "api_docs": "/docs",
            "features": {
                "manual_processing_only": True,
                "detailed_email_logging": True,
                "enhanced_function_calls": True
            }
        }

if __name__ == "__main__":
    print("🚀 Starting AIREA Enhanced API Server...")
    print("📧 Email processing: MANUAL ONLY")
    print("🔧 Enhanced logging: ENABLED")
    print("📊 Function calls: IMPROVED")
    uvicorn.run(app, host="0.0.0.0", port=8000)