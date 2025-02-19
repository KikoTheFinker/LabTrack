from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProfessorCourses(Base):
    __tablename__ = "professor_courses"

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)

    professor = relationship("User", back_populates="professor_courses")
    course = relationship("Course", back_populates="professor_courses")

    __table_args__ = (UniqueConstraint("professor_id", "course_id", name="uq_professor_course"),)
