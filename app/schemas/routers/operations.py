from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Абсолютные импорты
import schemas
import crud
import auth
from database import get_db

router = APIRouter()

@router.post("/start")
def start_operation(
    operation_data: schemas.OperationStartRequest,
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user)
):
    try:
        result = crud.start_operation(db, operation_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/confirm")
def confirm_operation(
    confirm_data: schemas.OperationConfirmRequest,
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user)
):
    try:
        result = crud.confirm_operation(db, confirm_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))