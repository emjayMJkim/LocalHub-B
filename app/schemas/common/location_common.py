from pydantic import BaseModel


class LocationListItemResponse(BaseModel):
    content_id: str
    title: str
    phone: str = " - "
    address: str = " - "
    image_url: str = ""
    mapx: float
    mapy: float
    createdtime: str