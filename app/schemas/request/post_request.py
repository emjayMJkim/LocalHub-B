from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    category: str = "DEFAULT"
    title: str = Field(min_length=1, max_length=100,)
    content: str = Field(min_length=1, max_length=5000,)
    password: str = Field(min_length=2, max_length=20,)

class PostDeleteRequest(BaseModel):
    password: str = Field(min_length=2, max_length=20,)