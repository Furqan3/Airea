from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional, Literal, Union, List, Dict, Any
from datetime import datetime
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import uvicorn
from pathlib import Path

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AIREA Real Estate Chatbot API",
    description="AI-powered real estate assistant with lead management",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini client
client = genai.Client(api_key="AIzaSyDfwjteT5fvuxPFiwG858ytXc-3rhlukFw")

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'theneuroscript@gmail.com',
    'sender_password': os.getenv('EMAIL_PASSWORD'),
    'sender_name': 'AIREA Real Estate',
    'agent_email': 'fahmad.ktk@gmail.com'
}

# Pydantic Models
class Client(BaseModel):
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
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for continuity")

class ChatResponse(BaseModel):
    message: str = Field(..., description="AI response")
    conversation_id: str = Field(..., description="Conversation ID")
    clients_processed: Optional[int] = Field(None, description="Number of clients processed")

class ConversationHistoryRequest(BaseModel):
    conversation_history: List[ChatMessage] = Field(..., description="Complete conversation history")

class ProcessDataResponse(BaseModel):
    clients_extracted: int = Field(..., description="Number of clients extracted")
    clients_processed: int = Field(..., description="Number of clients successfully processed")
    success: bool = Field(..., description="Overall success status")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")

class ClientResponse(BaseModel):
    clients: List[Client] = Field(..., description="List of clients")
    total_count: int = Field(..., description="Total number of clients")

# Global conversation storage (in production, use Redis or database)
conversations: Dict[str, List[ChatMessage]] = {}

class DatabaseManager:
    def __init__(self, db_path='real_estate_clients.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_type TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                property_type TEXT,
                address TEXT,
                budget REAL,
                appointment BOOLEAN,
                appointment_time TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_email TEXT NOT NULL,
                interaction_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_email) REFERENCES clients(email)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def client_exists(self, email: str) -> bool:
        """Check if a client already exists in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM clients WHERE email = ?', (email,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def save_client(self, client_data: Client) -> bool:
        """Save or update client data in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            appointment_time_str = client_data.appointment_time.isoformat() if client_data.appointment_time else None
            
            if self.client_exists(client_data.email):
                # Update existing client
                cursor.execute('''
                    UPDATE clients SET
                        client_type = ?,
                        name = ?,
                        phone = ?,
                        property_type = ?,
                        address = ?,
                        budget = ?,
                        appointment = ?,
                        appointment_time = ?,
                        details = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                ''', (
                    client_data.client_type,
                    client_data.name,
                    client_data.phone,
                    client_data.property_type,
                    client_data.address,
                    client_data.budget,
                    client_data.appointment,
                    appointment_time_str,
                    client_data.details,
                    client_data.email
                ))
                is_new = False
            else:
                # Insert new client
                cursor.execute('''
                    INSERT INTO clients (
                        client_type, name, phone, email, property_type,
                        address, budget, appointment, appointment_time, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    client_data.client_type,
                    client_data.name,
                    client_data.phone,
                    client_data.email,
                    client_data.property_type,
                    client_data.address,
                    client_data.budget,
                    client_data.appointment,
                    appointment_time_str,
                    client_data.details
                ))
                is_new = True
            
            conn.commit()
            return is_new
        except Exception as e:
            print(f"Database error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
        columns = [description[0] for description in cursor.description]
        clients = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return clients
    
    def save_interaction(self, email: str, interaction_data: str):
        """Save conversation history for a client"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO interactions (client_email, interaction_data)
                VALUES (?, ?)
            ''', (email, interaction_data))
            conn.commit()
        except Exception as e:
            print(f"Error saving interaction: {e}")
            conn.rollback()
        finally:
            conn.close()

class EmailService:
    def __init__(self, config: dict):
        self.config = config
    
    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Send an email using SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.config['sender_name'], self.config['sender_email']))
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
            
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['sender_email'], self.config['sender_password'])
                server.send_message(msg)
            
            print(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_welcome_email(self, client_data: Client):
        """Send welcome email to new client"""
        subject = "Welcome to AIREA Real Estate!"
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Welcome to AIREA Real Estate, {client_data.name}!</h2>
                    
                    <p>Thank you for choosing us as your real estate partner. We're excited to help you with your property needs.</p>
                    
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #34495e;">Your Profile Information:</h3>
                        <ul style="list-style-type: none; padding: 0;">
                            <li><strong>Client Type:</strong> {client_data.client_type}</li>
                            <li><strong>Email:</strong> {client_data.email}</li>
                            <li><strong>Phone:</strong> {client_data.phone}</li>
                            {'<li><strong>Property Type Interest:</strong> ' + str(client_data.property_type) + '</li>' if client_data.property_type else ''}
                            {'<li><strong>Budget:</strong> $' + f'{client_data.budget:,.2f}' + '</li>' if client_data.budget else ''}
                        </ul>
                    </div>
                    
                    <p>Our team will be in touch with you shortly to discuss your requirements in detail.</p>
                    
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #7f8c8d; font-size: 12px;">
                            Best regards,<br>
                            AIREA Real Estate Team<br>
                            Email: {self.config['sender_email']}<br>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        self.send_email(client_data.email, subject, body, is_html=True)
    
    def send_property_details_email(self, client_data: Client):
        """Send property details/appointment confirmation email"""
        if client_data.appointment and client_data.appointment_time:
            subject = "Appointment Confirmation - AIREA Real Estate"
            appointment_info = f"""
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2e7d32;">Appointment Scheduled!</h3>
                    <p><strong>Date & Time:</strong> {client_data.appointment_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                    {'<p><strong>Location:</strong> ' + client_data.address + '</p>' if client_data.address else ''}
                </div>
            """
        else:
            subject = "Property Interest Details - AIREA Real Estate"
            appointment_info = ""
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Property Interest Details</h2>
                    
                    <p>Dear {client_data.name},</p>
                    
                    <p>Thank you for your interest in our real estate services. Here's a summary of your requirements:</p>
                    
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #34495e;">Your Requirements:</h3>
                        <ul style="list-style-type: none; padding: 0;">
                            <li><strong>Looking to:</strong> {client_data.client_type}</li>
                            {'<li><strong>Property Type:</strong> ' + client_data.property_type + '</li>' if client_data.property_type else ''}
                            {'<li><strong>Budget:</strong> $' + f'{client_data.budget:,.2f}' + '</li>' if client_data.budget else ''}
                            {'<li><strong>Location:</strong> ' + client_data.address + '</li>' if client_data.address else ''}
                        </ul>
                    </div>
                    
                    {appointment_info}
                    
                    {'<div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;"><h4>Additional Notes:</h4><p>' + client_data.details + '</p></div>' if client_data.details else ''}
                    
                    <p>Our agent will contact you shortly to provide you with tailored property options that match your requirements.</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #7f8c8d; font-size: 12px;">
                            Best regards,<br>
                            AIREA Real Estate Team<br>
                            Email: {self.config['sender_email']}<br>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        self.send_email(client_data.email, subject, body, is_html=True)
    
    def send_agent_notification(self, client_data: Client, is_new_client: bool):
        """Send notification to the agent about new lead/appointment"""
        subject = f"{'New Client' if is_new_client else 'Returning Client'} - {client_data.name}"
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">{'New' if is_new_client else 'Returning'} Client Alert</h2>
                    
                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #1565c0;">Client Information:</h3>
                        <ul style="list-style-type: none; padding: 0;">
                            <li><strong>Name:</strong> {client_data.name}</li>
                            <li><strong>Email:</strong> {client_data.email}</li>
                            <li><strong>Phone:</strong> {client_data.phone}</li>
                            <li><strong>Type:</strong> {client_data.client_type}</li>
                        </ul>
                    </div>
                    
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #34495e;">Property Requirements:</h3>
                        <ul style="list-style-type: none; padding: 0;">
                            {'<li><strong>Property Type:</strong> ' + client_data.property_type + '</li>' if client_data.property_type else '<li>Property type not specified</li>'}
                            {'<li><strong>Budget:</strong> $' + f'{client_data.budget:,.2f}' + '</li>' if client_data.budget else '<li>Budget not specified</li>'}
                            {'<li><strong>Location:</strong> ' + client_data.address + '</li>' if client_data.address else '<li>Location not specified</li>'}
                        </ul>
                    </div>
                    
                    {f'''<div style="background-color: #fff9c4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #f57c00;">⚠️ Appointment Scheduled</h3>
                        <p><strong>Date & Time:</strong> {client_data.appointment_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                    </div>''' if client_data.appointment and client_data.appointment_time else ''}
                    
                    {'<div style="background-color: #fce4ec; padding: 15px; border-radius: 5px; margin: 20px 0;"><h4>Client Notes:</h4><p>' + client_data.details + '</p></div>' if client_data.details else ''}
                    
                    <p style="font-weight: bold; color: #d32f2f;">Please follow up with this client as soon as possible.</p>
                </div>
            </body>
        </html>
        """
        
        self.send_email(self.config['agent_email'], subject, body, is_html=True)

# Initialize services
db_manager = DatabaseManager()
email_service = EmailService(EMAIL_CONFIG)

def get_database():
    return db_manager

def get_email_service():
    return email_service

def extract_real_estate_data(input_data: Union[dict, str, List[ChatMessage]]):
    """Extract client data from conversation"""
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=f"""Extract the data from the conversation between AIREA and the user.
        conversation: {input_data}""",
        config={
            "response_mime_type": "application/json",
            "response_schema": list[Client],
        }
    )
    return response

def chat_with_user(input_data: str) -> str:
    """Generate AI response for user input"""
    try:
        with open("systempromt.txt", "r") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        # Default system prompt if file not found
        system_prompt = """You are AIREA, a friendly and professional real estate assistant. 
        Help users with their property needs - buying, selling, or renting. 
        Collect essential information like name, contact details, property preferences, budget, and location.
        Be conversational and helpful while gathering the necessary information."""
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt
        ),
        contents=str(input_data)
    )
    return response

def process_client_data(clients_list: List[Client], db_manager: DatabaseManager, email_service: EmailService):
    """Process extracted client data: save to DB and send emails"""
    processed_count = 0
    errors = []
    
    for client_data in clients_list:
        try:
            # Check if client is new and save to database
            is_new_client = db_manager.save_client(client_data)
            
            if is_new_client:
                print(f"New client added: {client_data.name} ({client_data.email})")
                # Send welcome email to new client
                email_service.send_welcome_email(client_data)
            else:
                print(f"Existing client updated: {client_data.name} ({client_data.email})")
            
            # Send property details/appointment email
            email_service.send_property_details_email(client_data)
            
            # Notify agent
            email_service.send_agent_notification(client_data, is_new_client)
            
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Error processing client {client_data.email}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    return processed_count, errors

# Create API Router
api_router = APIRouter(prefix="/api")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "AIREA Real Estate Chatbot API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@api_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: DatabaseManager = Depends(get_database)):
    """Main chat endpoint for conversing with the AI assistant"""
    try:
        # Generate conversation ID if not provided
        conv_id = request.conversation_id or f"conv_{datetime.now().timestamp()}"
        
        # Get or create conversation history
        if conv_id not in conversations:
            conversations[conv_id] = []
        
        # Add user message to history
        conversations[conv_id].append(ChatMessage(role="user", content=request.message))
        
        # Generate AI response
        response = chat_with_user(conversations[conv_id])
        ai_message = response.text
        
        # Add AI response to history
        conversations[conv_id].append(ChatMessage(role="assistant", content=ai_message))
        
        return ChatResponse(
            message=ai_message,
            conversation_id=conv_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@api_router.post("/process-conversation", response_model=ProcessDataResponse)
async def process_conversation_endpoint(
    request: ConversationHistoryRequest,
    db: DatabaseManager = Depends(get_database),
    email_service: EmailService = Depends(get_email_service)
):
    """Process a complete conversation to extract and save client data"""
    try:
        # Extract client data from conversation
        data_response = extract_real_estate_data(request.conversation_history)
        
        if not data_response.parsed:
            return ProcessDataResponse(
                clients_extracted=0,
                clients_processed=0,
                success=True,
                errors=["No client data extracted from the conversation."]
            )
        
        clients_list = data_response.parsed
        clients_extracted = len(clients_list)
        
        # Process clients (save to DB and send emails)
        processed_count, errors = process_client_data(clients_list, db, email_service)
        
        # Save conversation history for each client
        for client_data in clients_list:
            try:
                db.save_interaction(client_data.email, json.dumps([msg.dict() for msg in request.conversation_history]))
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
    db: DatabaseManager = Depends(get_database),
    email_service: EmailService = Depends(get_email_service)
):
    """Process a conversation by conversation ID"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    request = ConversationHistoryRequest(conversation_history=conversations[conversation_id])
    return await process_conversation_endpoint(request, db, email_service)

@api_router.get("/clients", response_model=ClientResponse)
async def get_clients(db: DatabaseManager = Depends(get_database)):
    """Get all clients from the database"""
    try:
        clients_data = db.get_all_clients()
        
        # Convert database records to Client models
        clients = []
        for client_data in clients_data:
            # Convert appointment_time string back to datetime if exists
            if client_data.get('appointment_time'):
                client_data['appointment_time'] = datetime.fromisoformat(client_data['appointment_time'])
            
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
async def get_conversation(conversation_id: str):
    """Get conversation history by ID"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id],
        "message_count": len(conversations[conversation_id])
    }

@api_router.get("/conversations")
async def list_conversations():
    """List all active conversations"""
    conv_list = []
    for conv_id, messages in conversations.items():
        conv_list.append({
            "conversation_id": conv_id,
            "message_count": len(messages),
            "last_message": messages[-1].dict() if messages else None
        })
    
    return {"conversations": conv_list, "total_count": len(conv_list)}

@api_router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversations[conversation_id]
    return {"message": f"Conversation {conversation_id} deleted successfully"}

# Include API router
app.include_router(api_router)

# Frontend serving routes
frontend_path = Path("frontend/out")

# Serve static files (CSS, JS, images, etc.)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "_next/static")), name="static_files")
    app.mount("/_next", StaticFiles(directory=str(frontend_path / "_next")), name="next_files")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve Next.js frontend files"""
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
        """Serve the main index.html"""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path, media_type="text/html")
        return {"message": "AIREA Real Estate Chatbot API", "version": "1.0.0", "note": "Frontend not found"}

else:
    @app.get("/")
    async def root_fallback():
        return {
            "message": "AIREA Real Estate Chatbot API", 
            "version": "1.0.0",
            "note": "Frontend directory not found. Please ensure 'frontend/out' exists.",
            "api_docs": "/docs"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)