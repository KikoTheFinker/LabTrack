from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base

class StudentPoints(Base):
    __tablename__ = "student_points"

    id = Column(Integer, primary_key=True, index=True)
    lab_exercise_id = Column(Integer, ForeignKey("laboratory_exercises.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, nullable=False)


    lab_exercise = relationship("LaboratoryExercise", backref="student_points")
    student = relationship("User", backref="student_points")
