#!/usr/bin/env python3

print("Testing simple model creation...")

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class SimpleUser(Base):
    __tablename__ = "simple_users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50))

print("SimpleUser class created:", SimpleUser)

# Test with SQLite
engine = create_engine("sqlite:///test_simple.db")
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

user = SimpleUser(username="test")
session.add(user)
session.commit()

print("User created with ID:", user.id)
session.close()

print("Simple model test successful!")