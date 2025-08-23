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
    
    def send_property_details_email(self, client_data: Client) -> bool:
        """Send property details/appointment confirmation email."""
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
    
    def send_agent_notification(self, client_data: Client, is_new_client: bool) -> bool:
        """Send notification to the agent about new lead/appointment."""
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