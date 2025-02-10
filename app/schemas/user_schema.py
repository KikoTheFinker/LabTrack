from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    surname: str

    class Config:
        from_attributes = True
