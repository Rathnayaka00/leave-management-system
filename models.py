from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Enum
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    sex = Column(Boolean)

class Leave(Base):
    __tablename__ = "leaves"
    id = Column(Integer, primary_key=True, index=True)
    leave_start_date = Column(Date, nullable=False)
    leave_day_count = Column(Integer, nullable=False)
    leave_type = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="Pending")  # e.g., Pending, Approved, Rejected
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String, nullable=False)

    user = relationship("User")