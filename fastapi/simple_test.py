#!/usr/bin/env python3
"""
Simple test to check imports
"""

try:
    print("Testing imports...")
    
    print("1. Importing datetime...")
    from datetime import datetime
    
    print("2. Importing SQLAlchemy...")
    from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON, Index
    from sqlalchemy.orm import relationship
    
    print("3. Importing app.db...")
    from app.db import Base
    
    print("4. Importing json...")
    import json
    
    print("5. Testing StringArray class...")
    from sqlalchemy import TypeDecorator, String as SQLString
    
    class StringArray(TypeDecorator):
        impl = Text
        cache_ok = True
        
        def process_bind_param(self, value, dialect):
            if value is not None:
                return json.dumps(value)
            return value
        
        def process_result_value(self, value, dialect):
            if value is not None:
                return json.loads(value)
            return value
    
    print("6. Testing User class definition...")
    class User(Base):
        __tablename__ = "users"
        
        id = Column(Integer, primary_key=True, index=True)
        username = Column(String(50), unique=True, nullable=False, index=True)
        email = Column(String(255), unique=True, nullable=False, index=True)
        hashed_password = Column(String(255), nullable=False)
        display_name = Column(String(100))
        bio = Column(Text)
        avatar_url = Column(String(500))
        is_active = Column(Boolean, default=True)
        is_verified = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    print("✓ All imports and class definition successful!")
    print(f"User class: {User}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()