import sqlite3
import json
import pandas as pd
from datetime import datetime

class UserContextDatabase:
    def __init__(self, db_path="user_context.db"):
        self.conn = sqlite3.connect(db_path,check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create necessary database tables if they don't exist"""
        # Users table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            income_level TEXT,
            budget string,
            favourite_colors TEXT,
            owned_assets TEXT,
            hobbies TEXT,
            preferred_brands TEXT,
            family_info TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        ''')
        
        # Conversations table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Messages table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            sender TEXT,
            message TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
        )
        ''')
        
        # User preferences table (for real estate preferences)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            min_price REAL,
            max_price REAL,
            min_area REAL,
            max_area REAL,
            preferred_districts TEXT,
            min_bedrooms INTEGER,
            min_bathrooms INTEGER,
            preferred_direction TEXT,
            legal_state TEXT,
            furniture_state TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Staff suggestions table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_suggestions (
            suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            message_id INTEGER,
            suggestion TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id),
            FOREIGN KEY (message_id) REFERENCES messages (message_id)
        )
        ''')
        
        self.conn.commit()

    def add_user(self, user_id, name=None, age=None, gender=None, income_level=None, budget=None, hobbies=None,
                favourite_colors=None, owned_assets=None, preferred_brands=None, family_info=None):   
        """Add a new user to the database"""
        now = datetime.now()
        
        # Convert list/dict fields to JSON strings
        favourite_colors = json.dumps(favourite_colors) if favourite_colors else None
        owned_assets = json.dumps(owned_assets) if owned_assets else None
        preferred_brands = json.dumps(preferred_brands) if preferred_brands else None
        family_info = json.dumps(family_info) if family_info else None
        
        self.cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, name, age, gender, income_level, budget, hobbies, favourite_colors,  owned_assets, 
         preferred_brands, family_info, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, age, gender, income_level, budget, hobbies, favourite_colors, owned_assets, 
             preferred_brands, family_info, now, now))
        
        self.conn.commit()
    
    def update_user(self, user_id, **kwargs):
        """Update user information"""
        now = datetime.now()
        
        # First, get current user data
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_data = self.cursor.fetchone()
        
        if not user_data:
            raise ValueError(f"User with ID {user_id} does not exist")
        
        # Prepare columns to update
        columns = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['favorite_colors', 'owned_assets', 'preferred_brands', 'family_info','hobbies'] and value is not None:
                value = json.dumps(value)
            columns.append(f"{key} = ?")
            values.append(value)
        
        # Add updated_at
        columns.append("updated_at = ?")
        values.append(now)
        
        # Construct and execute update query
        query = f"UPDATE users SET {', '.join(columns)} WHERE user_id = ?"
        values.append(user_id)
        
        self.cursor.execute(query, values)
        self.conn.commit()
    
    def add_user(self, user_id, name=None, age=None, gender=None, income_level=None, budget=None, hobbies=None,
             favourite_colors=None, owned_assets=None, preferred_brands=None, family_info=None):   
        """Add a new user to the database"""
        now = datetime.now()
        
        # Convert list/dict fields to JSON strings
        favourite_colors = json.dumps(favourite_colors) if favourite_colors else None
        owned_assets = json.dumps(owned_assets) if owned_assets else None
        preferred_brands = json.dumps(preferred_brands) if preferred_brands else None
        family_info = json.dumps(family_info) if family_info else None
        
        # Insert or replace user data
        self.cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, name, age, gender, income_level, budget, hobbies, favourite_colors, owned_assets, 
        preferred_brands, family_info, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, age, gender, income_level, budget, hobbies, favourite_colors, owned_assets, 
            preferred_brands, family_info, now, now))
    
        self.conn.commit()
    
    def create_conversation(self, conversation_id, user_id):
        """Create a new conversation"""
        now = datetime.now()
        
        self.cursor.execute('''
        INSERT INTO conversations (conversation_id, user_id, start_time, end_time)
        VALUES (?, ?, ?, NULL)
        ''', (conversation_id, user_id, now))
        
        self.conn.commit()
    
    def end_conversation(self, conversation_id):
        """Mark a conversation as ended"""
        now = datetime.now()
        
        self.cursor.execute('''
        UPDATE conversations SET end_time = ? WHERE conversation_id = ?
        ''', (now, conversation_id))
        
        self.conn.commit()
    
    def add_message(self, conversation_id, sender, message):
        """Add a message to a conversation"""
        now = datetime.now()
        
        self.cursor.execute('''
        INSERT INTO messages (conversation_id, sender, message, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (conversation_id, sender, message, now))
        
        message_id = self.cursor.lastrowid
        self.conn.commit()
        
        return message_id
    
    def add_staff_suggestion(self, conversation_id, message_id, suggestion):
        """Add a staff suggestion"""
        now = datetime.now()
        
        self.cursor.execute('''
        INSERT INTO staff_suggestions (conversation_id, message_id, suggestion, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (conversation_id, message_id, suggestion, now))
        
        self.conn.commit()
    
    def update_user_preferences(self, user_id, **kwargs):
        """Update user real estate preferences"""
        now = datetime.now()
        
        # Check if preferences exist for this user
        self.cursor.execute('''
        SELECT * FROM user_preferences WHERE user_id = ?
        ''', (user_id,))
        
        preferences = self.cursor.fetchone()
        
        if preferences:
            # Update existing preferences
            columns = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['preferred_districts', 'furniture_state', 'legal_state'] and value is not None:
                    value = json.dumps(value)
                columns.append(f"{key} = ?")
                values.append(value)
            
            
            
            # Construct and execute update query
            query = f"UPDATE user_preferences SET {', '.join(columns)} WHERE user_id = ?"
            values.append(user_id)
            
            self.cursor.execute(query, values)
        else:
            # Insert new preferences
            min_price = kwargs.get('min_price')
            max_price = kwargs.get('max_price')
            min_area = kwargs.get('min_area')
            max_area = kwargs.get('max_area')
            preferred_districts = json.dumps(kwargs.get('preferred_districts', [])) if 'preferred_districts' in kwargs else None
            min_bedrooms = kwargs.get('min_bedrooms')
            min_bathrooms = kwargs.get('min_bathrooms')
            preferred_direction = kwargs.get('preferred_direction')
            furniture_state = kwargs.get('furniture_state')
            legal_state = kwargs.get('legal_state')
            
            
            self.cursor.execute('''
            INSERT INTO user_preferences
            (user_id, min_price, max_price, min_area, max_area, preferred_districts,
             min_bedrooms, min_bathrooms, preferred_direction, furniture_state, legal_state )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, min_price, max_price, min_area, max_area, preferred_districts,
                 min_bedrooms, min_bathrooms, preferred_direction, furniture_state, legal_state))
        
        self.conn.commit()
    
    def get_user(self, user_id):
        """Retrieve user information"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_data = self.cursor.fetchone()
        
        if not user_data:
            return None
        
        # Column names
        columns = [desc[0] for desc in self.cursor.description]
        user_dict = dict(zip(columns, user_data))
        
        # Parse JSON fields
        for field in ['favourite_colors', 'owned_assets', 'preferred_brands', 'family_info']:
            if user_dict[field]:
                user_dict[field] = json.loads(user_dict[field])
        
        # The `hobbies` field is already in plain text, no need to decode
        return user_dict

    def get_user_preferences(self, user_id):
        """Retrieve user preferences from the database"""
        try:
            query = "SELECT * FROM user_preferences WHERE user_id = ?"
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()  # Fetch a single row

            if result:
                # If `result` is a tuple, map it to column names
                column_names = [desc[0] for desc in self.cursor.description]
                preferences_dict = dict(zip(column_names, result))
                return preferences_dict
            else:
                return None  # No preferences found

        except Exception as e:
            return None
    
    def get_conversation_history(self, conversation_id, limit=50):
        """Get recent conversation history"""
        self.cursor.execute('''
        SELECT * FROM messages 
        WHERE conversation_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (conversation_id, limit))
        
        messages = self.cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [desc[0] for desc in self.cursor.description]
        messages = [dict(zip(columns, message)) for message in messages]
        
        # Sort by timestamp (oldest first)
        messages.sort(key=lambda x: x['timestamp'])
        
        return messages
    # Add these new methods to the UserContextDatabase class

    def get_active_conversations(self):
        """Get all active conversations with their recent messages"""
        self.cursor.execute('''
        SELECT c.conversation_id, c.user_id, c.start_time,
            m.sender, m.message, m.timestamp
        FROM conversations c
        LEFT JOIN messages m ON c.conversation_id = m.conversation_id
        WHERE c.end_time IS NULL
        ORDER BY c.start_time DESC, m.timestamp DESC
        ''')
        
        conversations = {}
        for row in self.cursor.fetchall():
            conv_id = row[0]
            if conv_id not in conversations:
                conversations[conv_id] = {
                    'conversation_id': conv_id,
                    'user_id': row[1],
                    'start_time': row[2],
                    'messages': []
                }
            if row[3]:  # if there are messages
                conversations[conv_id]['messages'].append({
                    'sender': row[3],
                    'message': row[4],
                    'timestamp': row[5]
                })
        
        return list(conversations.values())

    def close(self):
        """Close the database connection"""
        self.conn.close()