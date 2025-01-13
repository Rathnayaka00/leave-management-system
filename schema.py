from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    sex: str

    class Config:
        from_attributes = True 

class UserResponse(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    sex: Optional[str]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LeaveCreate(BaseModel):
    leave_start_date: date
    leave_day_count: int
    leave_type: str
    reason: str

class LeaveResponse(BaseModel):
    id: int
    leave_start_date: date
    leave_day_count: int
    leave_type: str
    reason: str
    status: str
    username: str
    explanation: Optional[str]  # Include explanation

    class Config:
        from_attributes = True

class RemainingLeaveCountResponse(BaseModel):
    sick_leaves: int
    casual_leaves: int
    annual_leaves: int
    other_leaves: int

    class Config:
        from_attributes = True
