from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Enum, CheckConstraint
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    sex = Column(Boolean, nullable=False) 

    leave_counts = relationship("RemainingLeaveCount", back_populates="user", uselist=False)

    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="username_min_length"),
        CheckConstraint("char_length(first_name) > 0", name="first_name_non_empty"),
        CheckConstraint("char_length(last_name) > 0", name="last_name_non_empty"),
    )

class RemainingLeaveCount(Base):
    __tablename__ = "remaining_leave_counts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    sick_leaves = Column(Integer, default=10, nullable=False)
    casual_leaves = Column(Integer, default=30, nullable=False)
    annual_leaves = Column(Integer, default=14, nullable=False)
    other_leaves = Column(Integer, default=30, nullable=False)

    user = relationship("User", back_populates="leave_counts")

    __table_args__ = (
        CheckConstraint("sick_leaves >= 0", name="sick_leaves_non_negative"),
        CheckConstraint("casual_leaves >= 0", name="casual_leaves_non_negative"),
        CheckConstraint("annual_leaves >= 0", name="annual_leaves_non_negative"),
        CheckConstraint("other_leaves >= 0", name="other_leaves_non_negative"),
    )

class Leave(Base):
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    leave_start_date = Column(Date, nullable=False)
    leave_day_count = Column(Integer, nullable=False)
    leave_type = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="Pending")
    explanation = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String, nullable=False)

    user = relationship("User")

    # Constraints for data validation
    __table_args__ = (
        CheckConstraint("leave_day_count > 0", name="leave_day_count_positive"),
        CheckConstraint(
            "leave_type IN ('Sick', 'Casual', 'Annual', 'Other')",
            name="valid_leave_type"
        ),
    )