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

    leave_counts = relationship("RemainingLeaveCount", back_populates="user", uselist=False)

class RemainingLeaveCount(Base):
    __tablename__ = "remaining_leave_counts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    sick_leaves = Column(Integer, default=10)
    casual_leaves = Column(Integer, default=30)
    annual_leaves = Column(Integer, default=14)
    other_leaves = Column(Integer, default=30)

    user = relationship("User", back_populates="leave_counts")

class Leave(Base):
    __tablename__ = "leaves"
    id = Column(Integer, primary_key=True, index=True)
    leave_start_date = Column(Date, nullable=False)
    leave_day_count = Column(Integer, nullable=False)
    leave_type = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="Pending")
    explanation = Column(String)  # New column for storing RAG explanation
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String, nullable=False)

    user = relationship("User")