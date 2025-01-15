from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from schema import UserCreate, Token, UserResponse, LeaveCreate, LeaveResponse, RemainingLeaveCountResponse
from services import get_password_hash, create_access_token, get_user, verify_password
from utils import get_current_user
from models import User, Leave, RemainingLeaveCount
from database import get_db
from fastapi.responses import JSONResponse
from typing import List
from rag_handler import handle_request 
import json
from vector_setup import vectorize_pdf
from pathlib import Path

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = get_user(db, username=user.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        db_email = db.query(User).filter(User.email == user.email).first()
        if db_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )

        if len(user.password) < 8 or not any(char.isdigit() for char in user.password) or not any(char.isupper() for char in user.password) or not any(char in '!@#$%^&*()_+' for char in user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain at least one number, one uppercase letter, and one special character"
            )

        sex = user.sex.lower()
        if sex not in ['male', 'female']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sex must be either 'male' or 'female'"
            )

        hashed_password = get_password_hash(user.password)
        sex_boolean = sex == "male"

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

    except Exception as e:
        db.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


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


@router.post("/leave/request", response_model=LeaveResponse)
async def request_leave(
    leave_data: LeaveCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        rag_response = json.loads(handle_request(leave_data.reason))
        
        if not rag_response or "output" not in rag_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error in processing leave request."
            )
        
        status = "Approved" if rag_response["output"] == "1" else "Rejected"
        explanation = rag_response.get("explanation", "No explanation provided.")

        if leave_data.leave_day_count <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave day count must be greater than 0."
            )

        new_leave = Leave(
            user_id=current_user.id,
            username=current_user.username,
            leave_start_date=leave_data.leave_start_date,
            leave_day_count=leave_data.leave_day_count,
            leave_type=leave_data.leave_type,
            reason=leave_data.reason,
            status=status,
            explanation=explanation
        )
        db.add(new_leave)
        db.commit()
        db.refresh(new_leave)

        if status == "Approved":
            await update_remaining_leaves_auto(new_leave.id, db, current_user)

        return new_leave

    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

async def update_remaining_leaves_auto(leave_id: int, db: Session, current_user: User):
    try:
        leave = db.query(Leave).filter(Leave.id == leave_id, Leave.user_id == current_user.id).first()
        if not leave:
            raise HTTPException(status_code=404, detail="Leave request not found.")
        
        if leave.status != "Approved":
            return 

        leave_counts = db.query(RemainingLeaveCount).filter(RemainingLeaveCount.user_id == current_user.id).first()
        if not leave_counts:
            raise HTTPException(status_code=404, detail="Leave counts not found for this user.")

        leave_types = {
            "Sick": leave_counts.sick_leaves,
            "Casual": leave_counts.casual_leaves,
            "Annual": leave_counts.annual_leaves,
            "Other": leave_counts.other_leaves
        }

        if leave.leave_type not in leave_types:
            raise HTTPException(status_code=400, detail="Invalid leave type.")
        
        available_leaves = leave_types[leave.leave_type]
        if available_leaves >= leave.leave_day_count:
            setattr(leave_counts, leave.leave_type.lower() + "_leaves", available_leaves - leave.leave_day_count)
        else:
            raise HTTPException(status_code=400, detail=f"Not enough {leave.leave_type} leaves.")

        db.commit()

    except HTTPException as e:
        raise e  
    except Exception as e:
        db.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/leave-counts", status_code=status.HTTP_200_OK, response_model=RemainingLeaveCountResponse)
async def get_remaining_leave_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  
):
    leave_counts = db.query(RemainingLeaveCount).filter(RemainingLeaveCount.user_id == current_user.id).first()

    if not leave_counts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave counts not found for the user {current_user.username}"
        )

    return RemainingLeaveCountResponse(
        sick_leaves=leave_counts.sick_leaves,
        casual_leaves=leave_counts.casual_leaves,
        annual_leaves=leave_counts.annual_leaves,
        other_leaves=leave_counts.other_leaves,
    )


@router.get("/leaves", response_model=List[LeaveResponse])
async def get_user_leaves(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    leaves = db.query(Leave).filter(Leave.user_id == current_user.id).all()
    if not leaves:
        return []
    return leaves
    
@router.post("/upload-policy-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
        file_path = Path(f"temp_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(await file.read())

        result = vectorize_pdf(str(file_path))

        file_path.unlink()

        return JSONResponse(content={"message": result})

    except Exception as e:
        return HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")