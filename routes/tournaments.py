# routes/tournaments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from models import Tournament, TournamentEntry, TournamentResult, Bot, User
from database import get_db
from auth import require_user
from tournament import run_tournament
import json

router = APIRouter()

router = APIRouter(prefix="/tournaments", tags=["Tournaments"])

@router.post("/", response_model=dict)
async def create_tournament(
    name: str,
    description: str = None,
    rounds: int = 3,
    bot_ids: List[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Create a new tournament"""
    tournament = Tournament(
        name=name,
        description=description,
        creator_id=current_user.id,
        rounds=rounds,
        status="pending"
    )
    
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    
    # If bot_ids provided, register them to the tournament
    if bot_ids:
        for bot_id in bot_ids:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                continue
            
            entry = TournamentEntry(
                tournament_id=tournament.id,
                bot_id=bot_id
            )
            db.add(entry)
        
        db.commit()
    
    return {
        "id": tournament.id,
        "name": tournament.name,
        "description": tournament.description,
        "created_at": tournament.created_at,
        "status": tournament.status,
        "rounds": tournament.rounds
    }

@router.post("/{tournament_id}/register", response_model=dict)
async def register_bot_to_tournament(
    tournament_id: int,
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Register a bot to participate in a tournament"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament.status != "pending":
        raise HTTPException(status_code=400, detail="Tournament already started or completed")
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check if bot is already registered
    existing_entry = db.query(TournamentEntry).filter(
        TournamentEntry.tournament_id == tournament_id,
        TournamentEntry.bot_id == bot_id
    ).first()
    
    if existing_entry:
        raise HTTPException(status_code=400, detail="Bot already registered to this tournament")
    
    entry = TournamentEntry(
        tournament_id=tournament_id,
        bot_id=bot_id
    )
    
    db.add(entry)
    db.commit()
    
    return {"message": "Bot registered successfully"}

@router.post("/{tournament_id}/start", response_model=dict)
async def start_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Start running a tournament"""
    tournament = db.query(Tournament).filter(
        Tournament.id == tournament_id,
        Tournament.creator_id == current_user.id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament.status != "pending":
        raise HTTPException(status_code=400, detail="Tournament already started or completed")
    
    # Get all registered bots
    entries = db.query(TournamentEntry).options(
        joinedload(TournamentEntry.bot)
    ).filter(TournamentEntry.tournament_id == tournament_id).all()
    
    if len(entries) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 bots to start tournament")
    
    # Update tournament status
    tournament.status = "running"
    tournament.started_at = datetime.utcnow()
    db.commit()
    
    # Get bot filenames for the tournament
    bot_files = [entry.bot.filename for entry in entries]
    
    try:
        # Run the tournament
        rankings = run_tournament(bot_files, tournament.rounds)
        
        # Save results
        for rank, (bot_name, stats) in enumerate(rankings, 1):
            # Find the entry for this bot
            entry = next((e for e in entries if e.bot.filename == bot_name), None)
            if not entry:
                continue
                
            result = TournamentResult(
                tournament_id=tournament_id,
                entry_id=entry.id,
                rank=rank,
                wins=stats.get('wins', 0),
                losses=stats.get('losses', 0),
                score=stats.get('score', 0)
            )
            
            db.add(result)
        
        # Mark tournament as completed
        tournament.status = "completed"
        tournament.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "completed",
            "rankings": [{
                "rank": rank,
                "bot_name": bot_name,
                "wins": stats.get('wins', 0),
                "losses": stats.get('losses', 0),
                "score": stats.get('score', 0)
            } for rank, (bot_name, stats) in enumerate(rankings, 1)]
        }
    
    except Exception as e:
        tournament.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Tournament failed: {str(e)}")

@router.get("/", response_model=List[dict])
async def list_tournaments(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """List all tournaments, optionally filtered by status"""
    query = db.query(Tournament).filter(Tournament.creator_id == current_user.id)
    
    if status:
        query = query.filter(Tournament.status == status)
    
    tournaments = query.order_by(Tournament.created_at.desc()).all()
    
    return [{
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "created_at": t.created_at,
        "status": t.status,
        "rounds": t.rounds,
        "started_at": t.started_at,
        "completed_at": t.completed_at
    } for t in tournaments]

@router.get("/{tournament_id}", response_model=dict)
async def get_tournament_details(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Get detailed information about a tournament including results"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Get entries and results
    entries = db.query(TournamentEntry).options(
        joinedload(TournamentEntry.bot)
    ).filter(TournamentEntry.tournament_id == tournament_id).all()
    
    results = []
    if tournament.status == "completed":
        result_records = db.query(TournamentResult).options(
            joinedload(TournamentResult.entry).joinedload(TournamentEntry.bot)
        ).filter(TournamentResult.tournament_id == tournament_id).order_by(TournamentResult.rank).all()
        
        results = [{
            "rank": r.rank,
            "bot_name": r.entry.bot.original_filename,
            "wins": r.wins,
            "losses": r.losses,
            "score": r.score
        } for r in result_records]
    
    return {
        "id": tournament.id,
        "name": tournament.name,
        "description": tournament.description,
        "created_at": tournament.created_at,
        "status": tournament.status,
        "rounds": tournament.rounds,
        "started_at": tournament.started_at,
        "completed_at": tournament.completed_at,
        "entries": [{
            "bot_id": e.bot.id,
            "bot_name": e.bot.original_filename,
            "registered_at": e.registered_at
        } for e in entries],
        "results": results
    }