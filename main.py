from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import raise_invalid_credentials, raise_user_not_found, raise_course_not_found
from app.core.jwt.security import verify_password, create_access_token
from app.models import Course
from app.models.user import User
from app.schemas.course_schema import CourseResponse
from app.schemas.user_schema import UserResponse
from app.models.course_assignments import CourseAssignments
from app.schemas.login_request import LoginRequest

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

    access_token = create_access_token(data={"sub": user.username}, role=user.role)
    return {"access_token": access_token}


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise_user_not_found()

    return UserResponse.model_validate(user)
    # return {"username": user.username, "name": user.name, "surname": user.surname}


@app.get("/courses")
def get_all_courses(db: Session = Depends(get_db)):
    try:
        courses = db.query(Course).all()
        return [CourseResponse.model_validate(course) for course in courses]
        # return [
        #     {"id": course.id, "name": course.name, "code": course.code, "semester": course.semester}
        #     for course in courses]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/courses/{course_id}")
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise_course_not_found()
    return CourseResponse.model_validate(course)


@app.get("/courses/{course_id}/students")
def get_course_students(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise_course_not_found()

    course_assignments = db.query(CourseAssignments).filter(CourseAssignments.course_id == course_id).all()

    if not course_assignments:
        return {"message": "No students enrolled in this course"}

    students = [assignment.student for assignment in course_assignments]
    return [UserResponse.model_validate(student) for student in students]
    # return [
    #     {"id": student.id, "username": student.username, "name": student.name, "surname": student.surname}
    #     for student in students]


@app.post("/courses/{course_id}/enroll")
def enroll_course(course_id: int, user_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise_course_not_found()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_user_not_found()

    existing_enrollment = db.query(CourseAssignments).filter(
        CourseAssignments.course_id == course_id,
        CourseAssignments.student_id == user_id).first()

    if existing_enrollment:
        raise HTTPException(status_code=400, detail="User already enrolled in this course")

    enrollment = CourseAssignments(student_id=user_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return {"message": "User enrolled successfully"}

# @app.get("/courses/{course_id}/exercises}")
# def get_course_exercises(course_id: int, db : Session = Depends()):
