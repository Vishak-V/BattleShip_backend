# models.py
from sqlalchemy import UUID, Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
import datetime

# Use the Base from database.py
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    oauth_provider = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    university = Column(String, nullable=True)
    
    # Relationship with Bot
    bots = relationship("Bot", back_populates="owner")
    
    # Relationships with Tournament and Match
    tournaments = relationship("Tournament", back_populates="creator")
    matches = relationship("Match", back_populates="creator")

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    filename = Column(String)  # Unique filename for storage
    original_filename = Column(String)  # Original name of uploaded file
    file_path = Column(String)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    description = Column(Text, nullable=True)
    
    # Relationship with User
    owner = relationship("User", back_populates="bots")
    
    # Relationships with Match
    matches_as_bot1 = relationship("Match", foreign_keys="Match.bot1_id", back_populates="bot1")
    matches_as_bot2 = relationship("Match", foreign_keys="Match.bot2_id", back_populates="bot2")
    matches_as_winner = relationship("Match", foreign_keys="Match.winner_id", back_populates="winner")
    
    # Relationship with TournamentEntry
    tournament_entries = relationship("TournamentEntry", back_populates="bot")

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    bot1_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"))
    bot2_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"))
    winner_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=True)
    rounds_to_play = Column(Integer, default=3)
    bot1_wins = Column(Integer, default=0)
    bot2_wins = Column(Integer, default=0)
    status = Column(String)  # pending, running, completed, failed
    game_logs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", back_populates="matches")
    bot1 = relationship("Bot", foreign_keys=[bot1_id], back_populates="matches_as_bot1")
    bot2 = relationship("Bot", foreign_keys=[bot2_id], back_populates="matches_as_bot2")
    winner = relationship("Bot", foreign_keys=[winner_id], back_populates="matches_as_winner")

class Tournament(Base):
    __tablename__ = "tournaments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    rounds = Column(Integer, default=3)
    status = Column(String)  # pending, running, completed, failed
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", back_populates="tournaments")
    entries = relationship("TournamentEntry", back_populates="tournament")
    results = relationship("TournamentResult", back_populates="tournament")

class TournamentEntry(Base):
    __tablename__ = "tournament_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"))
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"))
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="entries")
    bot = relationship("Bot", back_populates="tournament_entries")
    result = relationship("TournamentResult", back_populates="entry", uselist=False)

class TournamentResult(Base):
    __tablename__ = "tournament_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"))
    entry_id = Column(UUID(as_uuid=True), ForeignKey("tournament_entries.id"))
    rank = Column(Integer)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    score = Column(Integer, default=0)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="results")
    entry = relationship("TournamentEntry", back_populates="result")