"""Database management for AIREA Real Estate Chatbot."""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import Client

class DatabaseManager:
    """Manages database operations for clients and interactions."""
    
    def __init__(self, db_path: str = 'real_estate_clients.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create clients table
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
            
            # Create interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_email TEXT NOT NULL,
                    interaction_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_email) REFERENCES clients(email)
                )
            ''')
            
            # Create conversations table for better conversation management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT UNIQUE NOT NULL,
                    messages TEXT NOT NULL,
                    client_email TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def client_exists(self, email: str) -> bool:
        """Check if a client already exists in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM clients WHERE email = ?', (email,))
            count = cursor.fetchone()[0]
            return count > 0
    
    def save_client(self, client_data: Client) -> bool:
        """Save or update client data in the database.
        
        Returns:
            bool: True if new client was created, False if existing client was updated
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                appointment_time_str = (
                    client_data.appointment_time.isoformat() 
                    if client_data.appointment_time else None
                )
                
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
                print(f"Database error saving client: {e}")
                conn.rollback()
                raise
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
            columns = [description[0] for description in cursor.description]
            clients = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return clients
    
    def get_client_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a specific client by email."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE email = ?', (email,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def save_interaction(self, email: str, interaction_data: str) -> None:
        """Save conversation history for a client."""
        with sqlite3.connect(self.db_path) as conn:
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
                raise
    
    def save_conversation(self, conversation_id: str, messages: List[Dict], client_email: Optional[str] = None) -> None:
        """Save or update conversation in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                messages_json = json.dumps(messages)
                
                # Check if conversation exists
                cursor.execute('SELECT id FROM conversations WHERE conversation_id = ?', (conversation_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing conversation
                    cursor.execute('''
                        UPDATE conversations SET
                            messages = ?,
                            client_email = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE conversation_id = ?
                    ''', (messages_json, client_email, conversation_id))
                else:
                    # Insert new conversation
                    cursor.execute('''
                        INSERT INTO conversations (conversation_id, messages, client_email)
                        VALUES (?, ?, ?)
                    ''', (conversation_id, messages_json, client_email))
                
                conn.commit()
            except Exception as e:
                print(f"Error saving conversation: {e}")
                conn.rollback()
                raise
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM conversations WHERE conversation_id = ?', (conversation_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                conversation = dict(zip(columns, row))
                # Parse messages JSON
                conversation['messages'] = json.loads(conversation['messages'])
                return conversation
            return None
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM conversations ORDER BY updated_at DESC')
            columns = [description[0] for description in cursor.description]
            conversations = []
            for row in cursor.fetchall():
                conversation = dict(zip(columns, row))
                # Parse messages JSON for summary
                messages = json.loads(conversation['messages'])
                conversation['message_count'] = len(messages)
                conversation['last_message'] = messages[-1] if messages else None
                conversations.append(conversation)
            return conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE conversation_id = ?', (conversation_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted