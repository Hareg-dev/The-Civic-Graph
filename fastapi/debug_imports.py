#!/usr/bin/env python3

print("Testing imports one by one...")

try:
    print("1. sqlalchemy imports...")
    from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON, Index
    print("✓ Basic SQLAlchemy imports OK")
    
    from sqlalchemy.orm import relationship
    print("✓ SQLAlchemy ORM imports OK")
    
    from sqlalchemy.dialects.postgresql import ARRAY
    print("✓ PostgreSQL dialect imports OK")
    
    from sqlalchemy import TypeDecorator, String as SQLString
    print("✓ TypeDecorator imports OK")
    
    from datetime import datetime
    print("✓ datetime imports OK")
    
    import json
    print("✓ json imports OK")
    
    print("2. app.db import...")
    from app.db import Base
    print("✓ app.db imports OK")
    
    print("3. Testing StringArray class...")
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
    
    print("✓ StringArray class OK")
    
    print("All imports successful!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()