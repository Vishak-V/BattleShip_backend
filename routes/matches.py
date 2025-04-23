# routes/matches.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from models import Match, Bot, User
from database import get_db
from auth import require_user
from tournament import run_tournament
import json

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post("/", response_model=dict)
async def create_match(
    bot1_id: str,
    bot2_id: str,
    rounds: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Create and run a match between two bots"""
    # Validate bots exist
    bot1 = db.query(Bot).filter(Bot.id == bot1_id).first()
    bot2 = db.query(Bot).filter(Bot.id == bot2_id).first()
    
    if not bot1 or not bot2:
        raise HTTPException(status_code=404, detail="One or both bots not found")
    
    # Create match record
    match = Match(
        id=uuid.uuid4(),
        creator_id=current_user.id,
        bot1_id=bot1_id,
        bot2_id=bot2_id,
        rounds_to_play=rounds,
        status="pending"
    )
    
    db.add(match)
    db.commit()
    db.refresh(match)
    
    # Run the match immediately
    try:
        match.status = "running"
        match.started_at = datetime.utcnow()
        db.commit()
        print(f"Match started between {bot1.filename} and {bot2.filename}")
        # Get bot filenames for the tournament engine
        bot_files = [bot1.filename, bot2.filename]
        rankings = run_tournament(bot_files, rounds)
        print(f"Match completed with rankings: {rankings}")
        # Process results
        match.status = "completed"
        match.completed_at = datetime.utcnow()
        
        if len(rankings) >= 2:
            winner_filename = rankings[0][0]
            winner_stats = rankings[0][1]
            loser_stats = rankings[1][1]
            
            # Determine winner
            winner_bot = bot1 if bot1.filename == winner_filename else bot2
            match.winner_id = winner_bot.id
            match.bot1_wins = winner_stats.get('wins', 0) if winner_bot == bot1 else loser_stats.get('wins', 0)
            match.bot2_wins = winner_stats.get('wins', 0) if winner_bot == bot2 else loser_stats.get('wins', 0)
            
            # Store game logs if available
            if 'logs' in winner_stats or 'logs' in loser_stats:
                match.game_logs = json.dumps({
                    'winner_logs': winner_stats.get('logs', []),
                    'loser_logs': loser_stats.get('logs', [])
                })
        
        db.commit()
        
        return {
            "id": match.id,
            "status": match.status,
            "bot1": {
                "id": bot1.id,
                "name": bot1.original_filename,
                "wins": match.bot1_wins
            },
            "bot2": {
                "id": bot2.id,
                "name": bot2.original_filename,
                "wins": match.bot2_wins
            },
            "winner_id": match.winner_id,
            "created_at": match.created_at,
            "completed_at": match.completed_at
        }
    
    except Exception as e:
        match.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Match failed: {str(e)}")

@router.get("/", response_model=List[dict])
async def list_matches(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """List all matches created by the current user"""
    query = db.query(Match).options(
        joinedload(Match.bot1),
        joinedload(Match.bot2),
        joinedload(Match.winner)
    ).filter(Match.creator_id == current_user.id)
    
    if status:
        query = query.filter(Match.status == status)
    
    matches = query.order_by(Match.created_at.desc()).all()
    
    return [{
        "id": m.id,
        "status": m.status,
        "bot1": {
            "id": m.bot1.id,
            "name": m.bot1.original_filename,
            "wins": m.bot1_wins
        },
        "bot2": {
            "id": m.bot2.id,
            "name": m.bot2.original_filename,
            "wins": m.bot2_wins
        },
        "winner": {
            "id": m.winner.id,
            "name": m.winner.original_filename
        } if m.winner else None,
        "created_at": m.created_at,
        "completed_at": m.completed_at
    } for m in matches]

@router.get("/{match_id}", response_model=dict)
async def get_match_details(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Get detailed information about a specific match"""
    match = db.query(Match).options(
        joinedload(Match.bot1),
        joinedload(Match.bot2),
        joinedload(Match.winner)
    ).filter(
        Match.id == match_id,
        Match.creator_id == current_user.id
    ).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    response = {
        "id": match.id,
        "status": match.status,
        "bot1": {
            "id": match.bot1.id,
            "name": match.bot1.original_filename,
            "wins": match.bot1_wins
        },
        "bot2": {
            "id": match.bot2.id,
            "name": match.bot2.original_filename,
            "wins": match.bot2_wins
        },
        "winner": {
            "id": match.winner.id,
            "name": match.winner.original_filename
        } if match.winner else None,
        "rounds_to_play": match.rounds_to_play,
        "created_at": match.created_at,
        "started_at": match.started_at,
        "completed_at": match.completed_at
    }
    
    # Include game logs if available
    if match.game_logs:
        try:
            response["game_logs"] = json.loads(match.game_logs)
        except:
            response["game_logs"] = match.game_logs
    
    return response

@router.post("/{match_id}/rematch", response_model=dict)
async def create_rematch(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Create a rematch using the same bots from a previous match"""
    original_match = db.query(Match).filter(
        Match.id == match_id,
        Match.creator_id == current_user.id
    ).first()
    
    if not original_match:
        raise HTTPException(status_code=404, detail="Original match not found")
    
    # Create new match with same parameters
    return await create_match(
        bot1_id=original_match.bot1_id,
        bot2_id=original_match.bot2_id,
        rounds=original_match.rounds_to_play,
        db=db,
        current_user=current_user
    )