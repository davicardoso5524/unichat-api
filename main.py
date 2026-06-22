from fastapi import FastAPI

from database.connection import engine
from database.base import Base

from users.model import User
from chats.model import Chat
from messages.model import Message
from chat_participants.model import ChatParticipant

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Unichat API",
    version="0.1.0",
)

@app.get("/")
def root():
    return {
        "message": "UniChat API is running"
    }