from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class CourseAssignments(Base):
    __tablename__ = "course_assignments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    time_details_id = Column(Integer, ForeignKey("time_details.id", ondelete="CASCADE"), nullable=False)

    student = relationship("User", backref="student_courses")
    course = relationship("Course", backref="student_courses")
    time_details = relationship("TimeDetails", backref="student_courses")
