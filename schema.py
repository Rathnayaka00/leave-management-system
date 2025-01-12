from pydantic import BaseModel, EmailStr
from typing import Optional

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
