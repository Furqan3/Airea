"""Email service for AIREA Real Estate Chatbot."""

import re
from typing import Dict, Any
from mailjet_rest import Client as MailjetClient
from models import Client

class MailjetEmailService:
    """Email service using Mailjet API."""
    
    def __init__(self, config: Dict[str, Any]):
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
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self.client is not None
    
    def send_email(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str = "") -> bool:
        """Send an email using Mailjet API."""
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
        """Convert HTML content to plain text (basic implementation)."""
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html_content)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Replace common HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text
    
    def send_welcome_email(self, client_data: Client) -> bool:
        """Send welcome email to new client."""
        subject = "Welcome to AIREA Real Estate"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to AIREA Real Estate</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white;">
                <!-- Header -->
                <div style="text-align: center; padding: 20px; border-bottom: 2px solid #53708B;">
                    <h1 style="margin: 0; font-size: 24px; color: #111827;">AIREA Real Estate</h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; color: #53708B;">Your Real Estate Partner</p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 30px 20px;">
                    <h2 style="color: #111827; margin-top: 0;">Welcome, {client_data.name}</h2>
                    
                    <p style="font-size: 16px; margin-bottom: 20px; color: #333;">
                        Thank you for choosing AIREA Real Estate. We're excited to help you with your real estate journey.
                    </p>
                    
                    <!-- Client Info -->
                    <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #111827; margin-top: 0; margin-bottom: 15px;">Your Information:</h3>
                        <p style="margin: 5px 0; color: #333;"><strong>Client Type:</strong> {client_data.client_type}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Email:</strong> {client_data.email}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Phone:</strong> {client_data.phone}</p>
                        {f'<p style="margin: 5px 0; color: #333;"><strong>Property Interest:</strong> {client_data.property_type}</p>' if client_data.property_type else ''}
                        {f'<p style="margin: 5px 0; color: #333;"><strong>Budget:</strong> ${client_data.budget:,.2f}</p>' if client_data.budget else ''}
                    </div>
                    
                    <p style="font-size: 16px; margin-bottom: 20px; color: #333;">
                        Our team will contact you shortly to discuss your requirements and provide personalized property recommendations.
                    </p>
                    
                    <p style="font-size: 16px; color: #333; margin-bottom: 0;">
                        If you have any questions, please contact us at {self.config['sender_email']}
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; border-top: 1px solid #E5E7EB; color: #666; font-size: 14px;">
                    <p style="margin: 0;">
                        AIREA Real Estate<br>
                        Email: {self.config['sender_email']}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Welcome to AIREA Real Estate, {client_data.name}

Thank you for choosing us as your real estate partner. We're excited to help you with your property needs.

Your Information:
- Client Type: {client_data.client_type}
- Email: {client_data.email}
- Phone: {client_data.phone}
{f'- Property Interest: {client_data.property_type}' if client_data.property_type else ''}
{f'- Budget: ${client_data.budget:,.2f}' if client_data.budget else ''}

Our team will contact you shortly to discuss your requirements and provide personalized property recommendations.

If you have any questions, please contact us at {self.config['sender_email']}

Best regards,
AIREA Real Estate Team
"""
        
        return self.send_email(client_data.email, client_data.name, subject, html_content, text_content)
    
    def send_property_details_email(self, client_data: Client) -> bool:
        """Send property details/appointment confirmation email."""
        if client_data.appointment and client_data.appointment_time:
            subject = "Appointment Confirmation - AIREA Real Estate"
            appointment_section = f"""
                <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #111827; margin-top: 0;">Appointment Scheduled</h3>
                    <p style="margin: 5px 0; color: #333;"><strong>Date & Time:</strong> {client_data.appointment_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                    {f'<p style="margin: 5px 0; color: #333;"><strong>Location:</strong> {client_data.address}</p>' if client_data.address else ''}
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
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white;">
                <!-- Header -->
                <div style="text-align: center; padding: 20px; border-bottom: 2px solid #53708B;">
                    <h1 style="margin: 0; font-size: 24px; color: #111827;">AIREA Real Estate</h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; color: #53708B;">Property Interest Details</p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 30px 20px;">
                    <p style="font-size: 16px; margin-bottom: 20px; color: #333;">Dear {client_data.name},</p>
                    
                    <p style="font-size: 16px; margin-bottom: 20px; color: #333;">
                        Thank you for your interest in our real estate services. Here are your requirements:
                    </p>
                    
                    <!-- Requirements -->
                    <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #111827; margin-top: 0; margin-bottom: 15px;">Your Requirements:</h3>
                        <p style="margin: 5px 0; color: #333;"><strong>Looking to:</strong> {client_data.client_type}</p>
                        {f'<p style="margin: 5px 0; color: #333;"><strong>Property Type:</strong> {client_data.property_type}</p>' if client_data.property_type else ''}
                        {f'<p style="margin: 5px 0; color: #333;"><strong>Budget:</strong> ${client_data.budget:,.2f}</p>' if client_data.budget else ''}
                        {f'<p style="margin: 5px 0; color: #333;"><strong>Location:</strong> {client_data.address}</p>' if client_data.address else ''}
                    </div>
                    
                    {appointment_section}
                    
                    {f'<div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;"><h4 style="color: #111827; margin-top: 0;">Additional Notes:</h4><p style="color: #333; margin-bottom: 0;">{client_data.details}</p></div>' if client_data.details else ''}
                    
                    <p style="font-size: 16px; margin-bottom: 20px; color: #333;">
                        Our agent will contact you shortly to provide tailored property options that match your requirements.
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; border-top: 1px solid #E5E7EB; color: #666; font-size: 14px;">
                    <p style="margin: 0;">
                        AIREA Real Estate<br>
                        Email: {self.config['sender_email']}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(client_data.email, client_data.name, subject, html_content)
    
    def send_agent_notification(self, client_data: Client, is_new_client: bool) -> bool:
        """Send notification to the agent about new lead/appointment."""
        subject = f"{'New Client Lead' if is_new_client else 'Client Update'} - {client_data.name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Client Alert</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white;">
                <!-- Header -->
                <div style="text-align: center; padding: 20px; border-bottom: 2px solid #53708B;">
                    <h1 style="margin: 0; font-size: 24px; color: #111827;">AIREA Real Estate</h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; color: #53708B;">{'New' if is_new_client else 'Returning'} Client Notification</p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 30px 20px;">
                    <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #111827; margin-top: 0; margin-bottom: 15px;">Client Information:</h3>
                        <p style="margin: 5px 0; color: #333;"><strong>Name:</strong> {client_data.name}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Email:</strong> {client_data.email}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Phone:</strong> {client_data.phone}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Type:</strong> {client_data.client_type}</p>
                    </div>
                    
                    <!-- Property Requirements -->
                    <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #111827; margin-top: 0; margin-bottom: 15px;">Property Requirements:</h3>
                        <p style="margin: 5px 0; color: #333;"><strong>Property Type:</strong> {client_data.property_type if client_data.property_type else 'Not specified'}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Budget:</strong> {f'${client_data.budget:,.2f}' if client_data.budget else 'Not specified'}</p>
                        <p style="margin: 5px 0; color: #333;"><strong>Location:</strong> {client_data.address if client_data.address else 'Not specified'}</p>
                    </div>
                    
                    {f'''
                    <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #111827; margin-top: 0;">Appointment Scheduled</h3>
                        <p style="margin: 5px 0; color: #333;"><strong>Date & Time:</strong> {client_data.appointment_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                        {f'<p style="margin: 5px 0; color: #333;"><strong>Meeting Location:</strong> {client_data.address}</p>' if client_data.address else ''}
                    </div>
                    ''' if client_data.appointment and client_data.appointment_time else ''}
                    
                    {f'<div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0;"><h4 style="color: #111827; margin-top: 0;">Client Notes:</h4><p style="color: #333; margin-bottom: 0;">{client_data.details}</p></div>' if client_data.details else ''}
                    
                    <div style="background-color: #E5E7EB; padding: 20px; margin: 20px 0; text-align: center;">
                        <h3 style="color: #111827; margin-top: 0; margin-bottom: 10px;">ACTION REQUIRED</h3>
                        <p style="color: #333; margin-bottom: 0;">Please follow up with this client as soon as possible.</p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; padding: 20px; border-top: 1px solid #E5E7EB; color: #666; font-size: 14px;">
                    <p style="margin: 0;">
                        AIREA Real Estate<br>
                        Agent Dashboard Alert System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(self.config['agent_email'], "AIREA Agent", subject, html_content)