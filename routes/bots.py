# routes/bots.py
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Form
from sqlalchemy import UUID
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from datetime import datetime
from models import User, Bot
from database import get_db
from auth import require_user
import uuid
from pathlib import Path

router = APIRouter(prefix="/bots", tags=["Bots"])

UPLOAD_DIR = "./uploads/"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)



@router.post("/", response_model=dict)
async def upload_bot(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Upload a new bot file"""
    
    # Generate unique filename to avoid collisions
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create database record
        bot = Bot(
            id=uuid.uuid4(),
            upload_date=datetime.utcnow(),
            is_active=True,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            description=description,
            uploader_id=current_user.id
        )
        print(f"Bot record created with ID: {bot.id}")
        
        db.add(bot)
        db.commit()
        db.refresh(bot)
        
        return {
            "id": bot.id,
            "filename": bot.original_filename,
            "upload_date": bot.upload_date,
            "description": bot.description
        }
    
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await file.close()

@router.get("/", response_model=List[dict])
async def list_bots(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """List all bots uploaded by the current user"""
    bots = db.query(Bot).filter(
        Bot.uploader_id == current_user.id,
        Bot.is_active == True
    ).order_by(Bot.upload_date.desc()).all()
    
    return [{
        "id": bot.id,
        "filename": bot.original_filename,
        "upload_date": bot.upload_date,
        "description": bot.description
    } for bot in bots]

@router.get("/{bot_id}", response_model=dict)
async def get_bot(
    bot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Get details for a specific bot"""
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.uploader_id == current_user.id
    ).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return {
        "id": bot.id,
        "filename": bot.original_filename,
        "upload_date": bot.upload_date,
        "description": bot.description,
        "is_active": bot.is_active
    }

@router.delete("/{bot_id}", response_model=dict)
async def delete_bot(
    bot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """Soft delete a bot (mark as inactive)"""
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.uploader_id == current_user.id
    ).first()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.is_active = False
    db.commit()
    
    return {"message": "Bot deleted successfully"}