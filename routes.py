from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from schema import UserCreate, Token, UserResponse, LeaveCreate, LeaveResponse
from services import get_password_hash, create_access_token, get_user, verify_password
from utils import get_current_user
from models import User, Leave
from database import get_db
from typing import List

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    sex_boolean = user.sex.lower() == "male"

    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        sex=sex_boolean
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully"}

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/leave/request", response_model=LeaveResponse)
async def request_leave(
    leave_data: LeaveCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    new_leave = Leave(
        user_id=current_user.id,
        username=current_user.username,
        leave_start_date=leave_data.leave_start_date,
        leave_day_count=leave_data.leave_day_count,
        leave_type=leave_data.leave_type,
        reason=leave_data.reason
    )
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    return new_leave

@router.get("/leaves", response_model=List[LeaveResponse])
async def get_user_leaves(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Query leave details for the current user
    leaves = db.query(Leave).filter(Leave.user_id == current_user.id).all()
    if not leaves:
        raise HTTPException(status_code=404, detail="No leave requests found for this user.")
    return leaves