from sqlalchemy import Column, Integer, String, LargeBinary
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(60), nullable=False)
    name = Column(String(50), nullable=True)
    surname = Column(String(50), nullable=True)
    role = Column(String(20), nullable=False)
    photo = Column(LargeBinary, nullable=True)
