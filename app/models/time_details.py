from sqlalchemy import Column, Integer, String, Time
from app.core.database import Base

class TimeDetails(Base):
    __tablename__ = "time_details"

    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String(50), nullable=False)
    room = Column(String(50), nullable=False)
    time = Column(Time, nullable=False)
