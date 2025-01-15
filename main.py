from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import raise_invalid_credentials
from app.core.jwt.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.LoginRequest import LoginRequest

app = FastAPI()


@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        return [
            {"id": user.id, "username": user.username, "name": user.name, "surname": user.surname, "role": user.role}
            for user in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/login")
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_request.username).first()
    if not user or not verify_password(login_request.password, user.password):
        raise_invalid_credentials()

    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}