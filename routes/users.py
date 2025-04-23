# routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from models import User, Bot, Tournament, Match
from sqlalchemy import func
from database import get_db
from auth import require_user

router = APIRouter(tags=["Users"])

@router.post("/user", response_model=List[dict])
async def create_user_profile(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Create a user profile"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.id == current_user.id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile already exists"
        )
    
    # Create new user profile
    new_user = User(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        oauth_provider=current_user.oauth_provider,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "oauth_provider": new_user.oauth_provider,
        "created_at": new_user.created_at,
        "last_login": new_user.last_login
    }

@router.get("/me", response_model=dict)
async def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Get the current user's profile information"""
    print(f"Current user ID: {current_user.id}")
    print(f"Current user email: {current_user.email}")
    try:
        # Get stats about user's activities
        bot_count = db.query(func.count(Bot.id)).filter(
            Bot.uploader_id == current_user.id,
            Bot.is_active == True
        ).scalar()
        print(f"Bot count: {bot_count}")
        tournament_count = db.query(func.count(Tournament.id)).filter(
            Tournament.creator_id == current_user.id
        ).scalar()
        print(f"Tournament count: {tournament_count}")
        match_count = db.query(func.count(Match.id)).filter(
            Match.creator_id == current_user.id
        ).scalar()
        print(f"Match count: {match_count}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user statistics",
            headers={"X-Error": str(e)}
        )
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "oauth_provider": current_user.oauth_provider,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
        "stats": {
            "bot_count": bot_count,
            "tournament_count": tournament_count,
            "match_count": match_count
        }
    }

@router.get("/me/stats", response_model=dict)
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Get detailed statistics for the current user"""
    # Get tournaments statistics
    tournaments_completed = db.query(func.count(Tournament.id)).filter(
        Tournament.creator_id == current_user.id,
        Tournament.status == "completed"
    ).scalar()
    
    tournaments_running = db.query(func.count(Tournament.id)).filter(
        Tournament.creator_id == current_user.id,
        Tournament.status == "running"
    ).scalar()
    
    tournaments_pending = db.query(func.count(Tournament.id)).filter(
        Tournament.creator_id == current_user.id,
        Tournament.status == "pending"
    ).scalar()
    
    # Get match statistics
    matches_completed = db.query(func.count(Match.id)).filter(
        Match.creator_id == current_user.id,
        Match.status == "completed"
    ).scalar()
    
    # Get winning rates (how often user's bots win)
    bot_ids = db.query(Bot.id).filter(
        Bot.uploader_id == current_user.id,
        Bot.is_active == True
    ).all()
    bot_ids = [bot.id for bot in bot_ids]
    
    total_matches_with_user_bots = 0
    wins_with_user_bots = 0
    
    if bot_ids:
        # Count matches where user's bots participated
        matches_with_user_bots = db.query(Match).filter(
            Match.status == "completed",
            (Match.bot1_id.in_(bot_ids) | Match.bot2_id.in_(bot_ids))
        ).all()
        
        total_matches_with_user_bots = len(matches_with_user_bots)
        
        # Count wins
        for match in matches_with_user_bots:
            if match.winner_id in bot_ids:
                wins_with_user_bots += 1
    
    win_rate = (wins_with_user_bots / total_matches_with_user_bots * 100) if total_matches_with_user_bots > 0 else 0
    
    return {
        "tournaments": {
            "total": tournaments_completed + tournaments_running + tournaments_pending,
            "completed": tournaments_completed,
            "running": tournaments_running,
            "pending": tournaments_pending
        },
        "matches": {
            "total": matches_completed,
            "completed": matches_completed
        },
        "bots": {
            "total": len(bot_ids),
            "win_rate": round(win_rate, 2),
            "total_matches_participated": total_matches_with_user_bots,
            "total_wins": wins_with_user_bots
        }
    }

@router.get("/me/recent-activity", response_model=List[dict])
async def get_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Get recent activity for the current user"""
    activities = []
    
    # Get recent bot uploads
    recent_bots = db.query(Bot).filter(
        Bot.uploader_id == current_user.id,
        Bot.is_active == True
    ).order_by(Bot.upload_date.desc()).limit(limit).all()
    
    for bot in recent_bots:
        activities.append({
            "type": "bot_upload",
            "timestamp": bot.upload_date,
            "details": {
                "bot_id": bot.id,
                "bot_name": bot.original_filename,
                "description": bot.description
            }
        })
    
    # Get recent tournaments
    recent_tournaments = db.query(Tournament).filter(
        Tournament.creator_id == current_user.id
    ).order_by(Tournament.created_at.desc()).limit(limit).all()
    
    for tournament in recent_tournaments:
        activities.append({
            "type": "tournament_created",
            "timestamp": tournament.created_at,
            "details": {
                "tournament_id": tournament.id,
                "tournament_name": tournament.name,
                "status": tournament.status
            }
        })
    
    # Get recent matches
    recent_matches = db.query(Match).filter(
        Match.creator_id == current_user.id
    ).order_by(Match.created_at.desc()).limit(limit).all()
    
    for match in recent_matches:
        activities.append({
            "type": "match_created",
            "timestamp": match.created_at,
            "details": {
                "match_id": match.id,
                "status": match.status,
                "bot1_id": match.bot1_id,
                "bot2_id": match.bot2_id,
                "winner_id": match.winner_id
            }
        })
    
    # Sort all activities by timestamp and return the most recent ones
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]

@router.put("/me", response_model=dict)
async def update_user_profile(
    name: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Update the current user's profile information"""
    if name:
        current_user.name = name
    
    current_user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "oauth_provider": current_user.oauth_provider,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }