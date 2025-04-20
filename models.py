# models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
import datetime

# Use the Base from main.py to ensure all models share the same Base
from main import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    oauth_provider = Column(String)
    oauth_id = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship with Bot
    bots = relationship("Bot", back_populates="owner")

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    display_name = Column(String)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    # Store bot description
    description = Column(Text, nullable=True)
    
    # Relationship with User
    owner = relationship("User", back_populates="bots")
    
    # Relationship with Tournament results
    results = relationship("TournamentResult", back_populates="bot")

class Tournament(Base):
    __tablename__ = "tournaments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationship with Tournament results
    results = relationship("TournamentResult", back_populates="tournament")
    created_by = relationship("User")
    
class TournamentResult(Base):
    __tablename__ = "tournament_results"
    
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    bot_id = Column(Integer, ForeignKey("bots.id"))
    rank = Column(Integer)
    score = Column(Integer)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="results")
    bot = relationship("Bot", back_populates="results")