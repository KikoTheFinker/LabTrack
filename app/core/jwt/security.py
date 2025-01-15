from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.exceptions import raise_jwt_invalid_or_expired, raise_user_not_found
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except JWTError:
        raise_jwt_invalid_or_expired()


def get_current_user(token: str, db: Session) -> User:
    try:
        payload = verify_access_token(token)
        email = payload.get("sub")
        if not email:
            raise_jwt_invalid_or_expired()

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise_user_not_found()

        return user

    except JWTError:
        raise_jwt_invalid_or_expired()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
