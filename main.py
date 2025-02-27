import base64
import io

import qrcode
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.exceptions import raise_invalid_credentials, raise_user_not_found, raise_course_not_found, \
    raise_user_not_permitted
from app.core.jwt.security import verify_password, create_access_token, get_current_user, hash_password
from app.models import Course, LaboratoryExercise, StudentPoints
from app.models import TimeDetails
from app.models.course_assignments import CourseAssignments
from app.models.professor_courses import ProfessorCourses
from app.models.user import User
from app.schemas.change_password_schema import ChangePasswordRequest
from app.schemas.course_schema import CourseResponse
from app.schemas.login_request import LoginRequest
from app.schemas.user_schema import UserResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/students")
def get_all_students(db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        raise_user_not_permitted()

    try:
        users = db.query(User).filter(User.role != "PROFESSOR", User.role != "ASSISTANT").all()
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
def get_user(user_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        raise_user_not_permitted()

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


@app.get("/student/{course_id}")
def get_course_current_user_exercises(course_id: int, db: Session = Depends(get_db),
                                      curr_user=Depends(get_current_user)):
    if curr_user.role not in ["STUDENT"]:
        raise_user_not_permitted()

    query = (
        db.query(
            CourseAssignments.id.label("assignment_id"),
            LaboratoryExercise.id.label("exercise_id"),
            LaboratoryExercise.name.label("exercise_name"),
            LaboratoryExercise.date_time.label("exercise_date"),
            LaboratoryExercise.max_points.label("exercise_max_points"),
            TimeDetails.id.label("time_details_id"),
            TimeDetails.group_name.label("time_details_group_name"),
            TimeDetails.room.label("time_details_room"),
            TimeDetails.time.label("time_details_time"),
            StudentPoints.points.label("student_points")
        )
        .join(LaboratoryExercise, LaboratoryExercise.course_id == CourseAssignments.course_id)
        .join(TimeDetails, TimeDetails.id == LaboratoryExercise.id)
        .outerjoin(StudentPoints,
                   (StudentPoints.lab_exercise_id == LaboratoryExercise.id) &
                   (StudentPoints.student_id == curr_user.id))
        .filter(CourseAssignments.student_id == curr_user.id)
        .filter(CourseAssignments.course_id == course_id)
    )

    results = query.all()

    response = {"assignments": []}

    for assignment_id, exercise_id, exercise_name, exercise_date, exercise_max_points, \
            time_details_id, time_details_group_name, time_details_room, time_details_time, student_points in results:
        response["assignments"].append({
            "assignment_id": assignment_id,
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "exercise_date": exercise_date,
            "exercise_max_points": exercise_max_points,
            "student_points": student_points if student_points is not None else "Not Graded",
            "time_details": {
                "time_details_id": time_details_id,
                "group_name": time_details_group_name,
                "room": time_details_room,
                "time": time_details_time,
            }
        })

    return response


@app.get("/courses/{course_id}/students")
def get_course_students(course_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        raise_user_not_permitted()

    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise_course_not_found()

    course_assignments = db.query(CourseAssignments).filter(CourseAssignments.course_id == course_id).all()

    if not course_assignments:
        return {"message": "No students enrolled in this course"}

    students = [assignment.student for assignment in course_assignments]

    return {"students": [UserResponse.model_validate(student) for student in students]}


@app.post("/courses/{course_id}/enroll")
def enroll_course(course_id: int, user_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        raise_user_not_permitted()

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


@app.get("/course/{user_id}")
def get_user_courses(user_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"] and curr_user.id != user_id:
        raise_user_not_permitted()


@app.get("/student/{course_id}")
def get_course_exercises(course_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    courses = (
        db.query(Course)
        .join(CourseAssignments, CourseAssignments.course_id == Course.id)
        .join(TimeDetails, TimeDetails.id == CourseAssignments.time_details_id)
        .filter(CourseAssignments.student_id == curr_user.id)
        .filter(Course.id == course_id)
        .options(joinedload(Course.assignments))
        .all()
    )
    return courses


@app.get("/my-courses")
def get_user_courses(db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        courses = (
            db.query(Course)
            .join(CourseAssignments, Course.id == CourseAssignments.course_id)
            .filter(CourseAssignments.student_id == curr_user.id)
            .all()
        )
    else:
        courses = (
            db.query(Course)
            .join(ProfessorCourses, Course.id == ProfessorCourses.course_id)
            .filter(ProfessorCourses.professor_id == curr_user.id)
            .all()
        )
    return {"courses": [{"course": course} for course in courses]}


@app.get("/student/{student_id}/courses-exercises")
def get_student_courses_exercises(student_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"] and curr_user.id != student_id:
        raise_user_not_permitted()

    query = (
        db.query(
            Course.id.label("course_id"),
            Course.name.label("course_name"),
            LaboratoryExercise.id.label("exercise_id"),
            LaboratoryExercise.name.label("exercise_name"),
            LaboratoryExercise.date_time.label("exercise_date"),
            LaboratoryExercise.max_points.label("exercise_max_points"),
            StudentPoints.points.label("points"),

        )
        .join(LaboratoryExercise, LaboratoryExercise.course_id == Course.id)
        .join(StudentPoints, StudentPoints.lab_exercise_id == LaboratoryExercise.id,
              isouter=True)
        .filter(StudentPoints.student_id == student_id)
    )

    results = query.all()

    response = {}
    for course_id, course_name, exercise_id, exercise_name, exercise_date, exercise_max_points, points in results:
        if course_id not in response:
            response[course_id] = {
                "course_id": course_id,
                "course_name": course_name,
                "exercises": []
            }

        response[course_id]["exercises"].append({
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "points": points if points is not None else "Not Graded",
            "max_points": exercise_max_points,
            "date": exercise_date
        })

    return list(response.values())


@app.get("/generate_qr/{lab_exercise_id}/{student_id}")
def generate_qr(lab_exercise_id: int, student_id: int, db: Session = Depends(get_db)):
    lab_exercise = db.query(LaboratoryExercise).filter(LaboratoryExercise.id == lab_exercise_id).first()
    if not lab_exercise:
        raise HTTPException(status_code=404, detail="Lab exercise not found")

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    gradind_url = f"http://127.0.0.1:8000/grade/{lab_exercise_id}/{student_id}"
    qr = qrcode.make(gradind_url)

    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {"qr_code": f"data:image/png;base64,{qr_base64}"}


@app.get("/grade/{lab_exercise_id}/{student_id}")
def get_grade_data(lab_exercise_id: int, student_id: int, db: Session = Depends(get_db),
                   curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        raise_user_not_permitted()

    student_points_data = (
        db.query(StudentPoints)
        .filter(StudentPoints.lab_exercise_id == lab_exercise_id, StudentPoints.student_id == student_id)
        .first()
    )

    if not student_points_data:
        new_student_points_data = StudentPoints(
            lab_exercise_id=lab_exercise_id,
            student_id=student_id,
            points=0
        )
        db.add(new_student_points_data)
        db.commit()
        db.refresh(new_student_points_data)
        student_points_data = new_student_points_data

    if not student_points_data:
        return {"message": "No record found"}

    return {
        "lab_exercise_id": student_points_data.lab_exercise_id,
        "student_id": student_points_data.student_id,
        "points": student_points_data.points
    }


@app.post("/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == curr_user.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(request.current_password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if request.new_password == request.current_password:
        raise HTTPException(status_code=400, detail="Current password is same")

    user.password = hash_password(request.new_password)
    db.commit()
    db.refresh(user)

    return {"message": "Password changed successfully!"}
