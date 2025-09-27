from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Абсолютные импорты
import schemas
import crud
import auth
from database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.ToolkitResponse])
def list_toolkits(
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user)
):
    toolkits = crud.get_toolkits(db)
    return toolkits

@router.get("/{toolkit_id}", response_model=schemas.ToolkitResponse)
def get_toolkit(
    toolkit_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user)
):
    toolkit = crud.get_toolkit(db, toolkit_id)
    if not toolkit:
        raise HTTPException(status_code=404, detail="Toolkit not found")
    return toolkit