from pydantic import BaseModel


class CategoryItemResponse(BaseModel):
    code: str
    name: str