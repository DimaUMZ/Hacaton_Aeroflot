from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import timedelta


import schemas
import crud
import auth
from database import get_db

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, login_data.badge_id, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect badge ID or password",
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.badge_id}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserResponse.from_orm(user)
    }

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: schemas.UserResponse = Depends(auth.get_current_active_user)):
    return current_user

@router.post("/demo-setup")
def setup_demo_data(db: Session = Depends(get_db)):
    try:
        crud.create_demo_data(db)
        return {"message": "Demo data created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating demo data: {str(e)}")