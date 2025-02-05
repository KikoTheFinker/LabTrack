from pydantic import BaseModel


class CourseResponse(BaseModel):
    name: str
    code: str
    semester: int

    class Config:
        from_attributes = True