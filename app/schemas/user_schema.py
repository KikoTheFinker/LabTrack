from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True
