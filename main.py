import qrcode
import io
import base64
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import raise_invalid_credentials, raise_user_not_found, raise_course_not_found, \
    raise_user_not_permitted
from app.core.jwt.security import verify_password, create_access_token, get_current_user
from app.models import Course, LaboratoryExercise, StudentPoints
from app.models.user import User
from app.schemas.change_password_schema import ChangePasswordRequest
from app.schemas.course_schema import CourseResponse
from app.schemas.user_schema import UserResponse
from app.models.course_assignments import CourseAssignments
from app.schemas.login_request import LoginRequest

app = FastAPI()


@app.get("/users")
def get_all_users(db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"]:
        raise_user_not_permitted()

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


@app.get("/courses/{course_id}")
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise_course_not_found()
    return CourseResponse.model_validate(course)


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
    return [UserResponse.model_validate(student) for student in students]
    # return [
    #     {"id": student.id, "username": student.username, "name": student.name, "surname": student.surname}
    #     for student in students]


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

# @app.get("/courses/{course_id}/exercises}")
# def get_course_exercises(course_id: int, db : Session = Depends()):


@app.get("/course/{user_id}")
def get_user_courses(user_id: int, db: Session = Depends(), curr_user=Depends(get_current_user)):
    if curr_user.role not in ["PROFESSOR", "ASSISTANT"] and curr_user.id != user_id:
        raise_user_not_permitted()

    courses = (
        db.query(Course)
        .join(CourseAssignments, Course.id == CourseAssignments.course_id)
        .filter(CourseAssignments.student_id == user_id)
        .distinct()
        .all()
    )

    return [
        {
            "course": course,
        }
        for course in courses
    ]


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
            StudentPoints.points.label("points"),
        )
        .join(LaboratoryExercise, LaboratoryExercise.course_id == Course.id)
        .join(StudentPoints, StudentPoints.lab_exercise_id == LaboratoryExercise.id,
              isouter=True)  # Left join to keep exercises without points
        .filter(StudentPoints.student_id == student_id)
    )

    results = query.all()

    response = {}
    for course_id, course_name, exercise_id, exercise_name, exercise_date, points in results:
        if course_id not in response:
            response[course_id] = {
                "course_id": course_id,
                "course_name": course_name,
                "exercises": []
            }

        response[course_id]["exercises"].append({
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "points": points if points is not None else 0,
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
def get_grade_data(lab_exercise_id: int, student_id: int, db: Session = Depends(get_db), curr_user=Depends(get_current_user)):
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

    # TODO: unhash curr_user's password and check if its same with request.current_password
    # TODO: check if request: new_password == request: confirm_new_password
    # TODO: exceptions for both if incorrect
    # TODO: hash new password if everything okay
    # Save new hashed password
    # user.password = hashed_password
    # db.commit()
    return {"message": "Password changed successfully!"}