from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional, Literal, Union, List, Dict, Any
from datetime import datetime
import json
import sqlite3
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import uvicorn
from pathlib import Path
from mailjet_rest import Client as MailjetClient
import re

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
    'mailjet_api_key': os.getenv('MAILJET_API_KEY'),
    'mailjet_secret_key': os.getenv('MAILJET_SECRET_KEY'),
    'sender_email': os.getenv('SENDER_EMAIL', 'info@askairea.com'),
    'sender_name': os.getenv('SENDER_NAME', 'AIREA Real Estate'),
    'agent_email': os.getenv('AGENT_EMAIL', 'agent@askairea.com')
}

# Validate email configuration
if not EMAIL_CONFIG['mailjet_api_key'] or not EMAIL_CONFIG['mailjet_secret_key']:
    print("Warning: Mailjet API credentials not found in environment variables")

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

class MailjetEmailService:
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        
        # Initialize Mailjet client if credentials are available
        if config['mailjet_api_key'] and config['mailjet_secret_key']:
            self.client = MailjetClient(
                auth=(config['mailjet_api_key'], config['mailjet_secret_key']),
                version='v3.1'
            )
        else:
            print("Warning: Mailjet client not initialized due to missing credentials")
    
    def send_email(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str = "") -> bool:
        """Send an email using Mailjet API"""
        if not self.client:
            print("Error: Mailjet client not initialized")
            return False
        
        try:
            data = {
                'Messages': [
                    {
                        "From": {
                            "Email": self.config['sender_email'],
                            "Name": self.config['sender_name']
                        },
                        "To": [
                            {
                                "Email": to_email,
                                "Name": to_name
                            }
                        ],
                        "Subject": subject,
                        "HTMLPart": html_content,
                        "TextPart": text_content or self._html_to_text(html_content)
                    }
                ]
            }
            
            result = self.client.send.create(data=data)
            
            if result.status_code == 200:
                print(f"Email sent successfully to {to_email}")
                return True
            else:
                print(f"Failed to send email. Status: {result.status_code}, Response: {result.json()}")
                return False
                
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text (basic implementation)"""
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html_content)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Replace common HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text
    
    def send_welcome_email(self, client_data: Client):
        """Send welcome email to new client"""
        subject = "Welcome to AIREA Real Estate!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to AIREA Real Estate</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 30px 20px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: bold;">AIREA</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Your AI Real Estate Assistant</p>
                </div>
                
                <!-- Main Content -->
                <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #2563eb; margin-top: 0;">Welcome, {client_data.name}! 🎉</h2>
                    
                    <p style="font-size: 16px; margin-bottom: 25px;">
                        Thank you for choosing AIREA Real Estate as your property partner. We're excited to help you with your real estate journey!
                    </p>
                    
                    <!-- Client Info Card -->
                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #2563eb;">
                        <h3 style="color: #1e293b; margin-top: 0; margin-bottom: 15px;">Your Profile Information:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #475569;">Client Type:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{client_data.client_type}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #475569;">Email:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{client_data.email}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #475569;">Phone:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{client_data.phone}</td>
                            </tr>
                            {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #475569;">Property Interest:</td><td style="padding: 8px 0; color: #1e293b;">{client_data.property_type}</td></tr>' if client_data.property_type else ''}
                            {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #475569;">Budget:</td><td style="padding: 8px 0; color: #1e293b;">${client_data.budget:,.2f}</td></tr>' if client_data.budget else ''}
                        </table>
                    </div>
                    
                    <p style="font-size: 16px; margin-bottom: 25px;">
                        Our expert team will be in touch with you shortly to discuss your requirements in detail and provide you with personalized property recommendations.
                    </p>
                    
                    <!-- CTA Button -->
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="mailto:{self.config['agent_email']}" style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">Contact Our Agent</a>
                    </div>
                    
                    <p style="font-size: 16px; color: #64748b; margin-bottom: 0;">
                        If you have any questions, please don't hesitate to reach out to us anytime.
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; color: #64748b; font-size: 14px;">
                    <p style="margin: 0;">
                        <strong>AIREA Real Estate</strong><br>
                        Email: {self.config['sender_email']}<br>
                        Making real estate simple with AI
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Welcome to AIREA Real Estate, {client_data.name}!

Thank you for choosing us as your real estate partner. We're excited to help you with your property needs.

Your Profile Information:
- Client Type: {client_data.client_type}
- Email: {client_data.email}
- Phone: {client_data.phone}
{f'- Property Interest: {client_data.property_type}' if client_data.property_type else ''}
{f'- Budget: ${client_data.budget:,.2f}' if client_data.budget else ''}

Our team will be in touch with you shortly to discuss your requirements in detail.

If you have any questions, please don't hesitate to contact us.

Best regards,
AIREA Real Estate Team
Email: {self.config['sender_email']}
"""
        
        return self.send_email(client_data.email, client_data.name, subject, html_content, text_content)
    
    def send_property_details_email(self, client_data: Client):
        """Send property details/appointment confirmation email"""
        if client_data.appointment and client_data.appointment_time:
            subject = "Appointment Confirmation - AIREA Real Estate"
            appointment_section = f"""
                <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: white; padding: 20px; border-radius: 8px; margin: 25px 0;">
                    <h3 style="margin-top: 0; color: white;">📅 Appointment Scheduled!</h3>
                    <p style="margin-bottom: 0; font-size: 16px;"><strong>Date & Time:</strong> {client_data.appointment_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                    {f'<p style="margin-bottom: 0; font-size: 16px;"><strong>Location:</strong> {client_data.address}</p>' if client_data.address else ''}
                </div>
            """
        else:
            subject = "Property Interest Details - AIREA Real Estate"
            appointment_section = ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Property Interest Details</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 30px 20px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: bold;">AIREA</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Property Interest Details</p>
                </div>
                
                <!-- Main Content -->
                <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="font-size: 18px; margin-bottom: 25px;">Dear {client_data.name},</p>
                    
                    <p style="font-size: 16px; margin-bottom: 25px;">
                        Thank you for your interest in our real estate services. Here's a summary of your requirements:
                    </p>
                    
                    <!-- Requirements Card -->
                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #3b82f6;">
                        <h3 style="color: #1e293b; margin-top: 0; margin-bottom: 15px;">🏠 Your Requirements:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #475569;">Looking to:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{client_data.client_type}</td>
                            </tr>
                            {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #475569;">Property Type:</td><td style="padding: 8px 0; color: #1e293b;">{client_data.property_type}</td></tr>' if client_data.property_type else ''}
                            {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #475569;">Budget:</td><td style="padding: 8px 0; color: #1e293b;">${client_data.budget:,.2f}</td></tr>' if client_data.budget else ''}
                            {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #475569;">Location:</td><td style="padding: 8px 0; color: #1e293b;">{client_data.address}</td></tr>' if client_data.address else ''}
                        </table>
                    </div>
                    
                    {appointment_section}
                    
                    {f'<div style="background-color: #fef7cd; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #f59e0b;"><h4 style="color: #92400e; margin-top: 0;">💬 Additional Notes:</h4><p style="color: #451a03; margin-bottom: 0;">{client_data.details}</p></div>' if client_data.details else ''}
                    
                    <p style="font-size: 16px; margin-bottom: 25px;">
                        Our expert agent will contact you shortly to provide you with tailored property options that perfectly match your requirements.
                    </p>
                    
                    <!-- CTA Button -->
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="mailto:{self.config['agent_email']}" style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">Contact Our Agent Directly</a>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; color: #64748b; font-size: 14px;">
                    <p style="margin: 0;">
                        <strong>AIREA Real Estate</strong><br>
                        Email: {self.config['sender_email']}<br>
                        Making real estate simple with AI
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(client_data.email, client_data.name, subject, html_content)
    
    def send_agent_notification(self, client_data: Client, is_new_client: bool):
        """Send notification to the agent about new lead/appointment"""
        subject = f"🚨 {'New Client Lead' if is_new_client else 'Returning Client Update'} - {client_data.name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Client Alert</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%); color: white; padding: 30px 20px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: bold;">🚨 CLIENT ALERT</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{'New' if is_new_client else 'Returning'} Client Notification</p>
                </div>
                
                <!-- Main Content -->
                <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="background-color: #dbeafe; padding: 20px; border-radius: 8px; margin: 0 0 25px 0; border-left: 4px solid #2563eb;">
                        <h3 style="color: #1e40af; margin-top: 0; margin-bottom: 15px;">👤 Client Information:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #1e40af;">Name:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-weight: bold;">{client_data.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #1e40af;">Email:</td>
                                <td style="padding: 8px 0; color: #1e293b;"><a href="mailto:{client_data.email}" style="color: #2563eb;">{client_data.email}</a></td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #1e40af;">Phone:</td>
                                <td style="padding: 8px 0; color: #1e293b;"><a href="tel:{client_data.phone}" style="color: #2563eb;">{client_data.phone}</a></td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #1e40af;">Type:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-weight: bold;">{client_data.client_type}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Property Requirements -->
                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #059669;">
                        <h3 style="color: #065f46; margin-top: 0; margin-bottom: 15px;">🏠 Property Requirements:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #065f46;">Property Type:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{client_data.property_type if client_data.property_type else 'Not specified'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #065f46;">Budget:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{f'${client_data.budget:,.2f}' if client_data.budget else 'Not specified'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #065f46;">Location:</td>
                                <td style="padding: 8px 0; color: #1e293b;">{client_data.address if client_data.address else 'Not specified'}</td>
                            </tr>
                        </table>
                    </div>
                    
                    {f'''
                    <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <h3 style="color: white; margin-top: 0;">⚠️ URGENT: Appointment Scheduled!</h3>
                        <p style="margin-bottom: 0; font-size: 16px;"><strong>Date & Time:</strong> {client_data.appointment_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                        {f'<p style="margin-bottom: 0; font-size: 16px;"><strong>Meeting Location:</strong> {client_data.address}</p>' if client_data.address else ''}
                    </div>
                    ''' if client_data.appointment and client_data.appointment_time else ''}
                    
                    {f'<div style="background-color: #fce4ec; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #e91e63;"><h4 style="color: #ad1457; margin-top: 0;">💬 Client Notes:</h4><p style="color: #4a148c; margin-bottom: 0;">{client_data.details}</p></div>' if client_data.details else ''}
                    
                    <div style="background-color: #fee2e2; padding: 20px; border-radius: 8px; margin: 25px 0; text-align: center; border-left: 4px solid #dc2626;">
                        <h3 style="color: #991b1b; margin-top: 0; margin-bottom: 10px;">🔥 ACTION REQUIRED</h3>
                        <p style="color: #7f1d1d; font-weight: bold; margin-bottom: 0;">Please follow up with this client as soon as possible!</p>
                    </div>
                    
                    <!-- Quick Action Buttons -->
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="mailto:{client_data.email}" style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px; font-weight: bold; display: inline-block; margin: 5px;">📧 Email Client</a>
                        <a href="tel:{client_data.phone}" style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px; font-weight: bold; display: inline-block; margin: 5px;">📞 Call Client</a>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; color: #64748b; font-size: 14px;">
                    <p style="margin: 0;">
                        <strong>AIREA Real Estate CRM</strong><br>
                        Agent Dashboard Alert System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(self.config['agent_email'], "AIREA Agent", subject, html_content)

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

def process_client_data(clients_list: List[Client], db_manager: DatabaseManager, email_service: MailjetEmailService):
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
                if not email_service.send_welcome_email(client_data):
                    errors.append(f"Failed to send welcome email to {client_data.email}")
            else:
                print(f"Existing client updated: {client_data.name} ({client_data.email})")
            
            # Send property details/appointment email
            if not email_service.send_property_details_email(client_data):
                errors.append(f"Failed to send property details email to {client_data.email}")
            
            # Notify agent
            if not email_service.send_agent_notification(client_data, is_new_client):
                errors.append(f"Failed to send agent notification for {client_data.email}")
            
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Error processing client {client_data.email}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    return processed_count, errors

# Initialize services
db_manager = DatabaseManager()
email_service = MailjetEmailService(EMAIL_CONFIG)

def get_database():
    return db_manager

def get_email_service():
    return email_service

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
    email_service: MailjetEmailService = Depends(get_email_service)
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
    email_service: MailjetEmailService = Depends(get_email_service)
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

@api_router.get("/email/test")
async def test_email(email_service: MailjetEmailService = Depends(get_email_service)):
    """Test email functionality"""
    if not email_service.client:
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
            "api_configured": bool(email_service.config['mailjet_api_key'])
        }
    }

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