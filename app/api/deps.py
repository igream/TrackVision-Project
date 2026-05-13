from fastapi import Request, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from app.core.config_backend import SESSION_COOKIE_NAME
from app.core.security import verify_session_token

def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    user_id = verify_session_token(session_token) if session_token else None
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None
