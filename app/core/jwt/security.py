from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, Depends
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.database import get_db
from app.core.exceptions import raise_jwt_invalid_or_expired, raise_user_not_found
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, role: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "role": role})
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


from fastapi import Header


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use 'Bearer <token>'."
        )

    token = authorization.split("Bearer ")[1]
    payload = verify_access_token(token)

    username = payload.get("sub")
    if not username:
        raise_jwt_invalid_or_expired()

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise_user_not_found()

    return user


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
