from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class LaboratoryExercise(Base):
    __tablename__ = "laboratory_exercises"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    date_time = Column(DateTime, nullable=False)
    max_points = Column(Integer, nullable=False)

    course = relationship("Course", backref="laboratory_exercises")
