from fastapi import FastAPI
from database import Base, engine
from routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Leave Management System API",
    description="An API for managing user registrations, leave requests, and policy management.",
    version="1.0.0"
)

app.include_router(router)

