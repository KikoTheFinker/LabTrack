from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(30), unique=True, nullable=False)
    semester = Column(Integer, nullable=False)
