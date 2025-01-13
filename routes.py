from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from schema import UserCreate, Token, UserResponse, LeaveCreate, LeaveResponse, RemainingLeaveCountResponse
from services import get_password_hash, create_access_token, get_user, verify_password
from utils import get_current_user
from models import User, Leave, RemainingLeaveCount
from database import get_db
from typing import List
from rag_handler import handle_request 
import json

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

    leave_counts = RemainingLeaveCount(user_id=db_user.id)
    db.add(leave_counts)
    db.commit()

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
    # Get RAG response
    rag_response = json.loads(handle_request(leave_data.reason))
    binary_result = rag_response.get("output", "0")
    explanation = rag_response.get("explanation", "No explanation provided.")

    # Determine leave status based on RAG output
    status = "Approved" if binary_result == "1" else "Rejected"

    new_leave = Leave(
        user_id=current_user.id,
        username=current_user.username,
        leave_start_date=leave_data.leave_start_date,
        leave_day_count=leave_data.leave_day_count,
        leave_type=leave_data.leave_type,
        reason=leave_data.reason,
        status=status,
        explanation=explanation  # Store the explanation
    )
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    return new_leave


@router.post("/leave/update")
async def update_remaining_leaves(
    leave_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    leave = db.query(Leave).filter(Leave.id == leave_id, Leave.user_id == current_user.id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if leave.status != "Approved":
        raise HTTPException(status_code=400, detail="Leave request is not approved.")
    

    leave_counts = db.query(RemainingLeaveCount).filter(RemainingLeaveCount.user_id == current_user.id).first()
    if not leave_counts:
        raise HTTPException(status_code=404, detail="Leave counts not found for this user.")
    
    if leave.leave_type == "Sick":
        if leave_counts.sick_leaves < leave.leave_day_count:
            raise HTTPException(status_code=400, detail="Not enough Sick leaves.")
        leave_counts.sick_leaves -= leave.leave_day_count
    elif leave.leave_type == "Casual":
        if leave_counts.casual_leaves < leave.leave_day_count:
            raise HTTPException(status_code=400, detail="Not enough Casual leaves.")
        leave_counts.casual_leaves -= leave.leave_day_count
    elif leave.leave_type == "Annual":
        if leave_counts.annual_leaves < leave.leave_day_count:
            raise HTTPException(status_code=400, detail="Not enough Annual leaves.")
        leave_counts.annual_leaves -= leave.leave_day_count
    elif leave.leave_type == "Other":
        if leave_counts.other_leaves < leave.leave_day_count:
            raise HTTPException(status_code=400, detail="Not enough Other leaves.")
        leave_counts.other_leaves -= leave.leave_day_count
    else:
        raise HTTPException(status_code=400, detail="Invalid leave type.")

    db.commit()
    return {"message": "Remaining leave count updated successfully."}

@router.get("/remaining-leaves/{user_id}", status_code=status.HTTP_200_OK)
def get_remaining_leaves(user_id: int, db: Session = Depends(get_db)):
    leave_counts = db.query(RemainingLeaveCount).filter(RemainingLeaveCount.user_id == user_id).first()

    if not leave_counts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave counts not found for user_id {user_id}"
        )

    return {
        "user_id": leave_counts.user_id,
        "username": leave_counts.username,
        "sick_leaves": leave_counts.sick_leaves,
        "casual_leaves": leave_counts.casual_leaves,
        "annual_leaves": leave_counts.annual_leaves,
        "other_leaves": leave_counts.other_leaves,
    }

@router.get("/leave-counts", status_code=status.HTTP_200_OK)
async def get_remaining_leave_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  
):
    leave_counts = db.query(RemainingLeaveCount).filter(RemainingLeaveCount.user_id == current_user.id).first()

    if not leave_counts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave counts not found for the user"
        )

    return {
        "username": current_user.username,
        "sick_leaves": leave_counts.sick_leaves,
        "casual_leaves": leave_counts.casual_leaves,
        "annual_leaves": leave_counts.annual_leaves,
        "other_leaves": leave_counts.other_leaves,
    }


@router.get("/leaves", response_model=List[LeaveResponse])
async def get_user_leaves(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    leaves = db.query(Leave).filter(Leave.user_id == current_user.id).all()
    if not leaves:
        raise HTTPException(status_code=404, detail="No leave requests found for this user.")
    return leaves