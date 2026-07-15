from pydantic import BaseModel


class LocationListItemResponse(BaseModel):
    title: str
    phone: str = " - "
    address: str = " - "
    image_url: str = ""