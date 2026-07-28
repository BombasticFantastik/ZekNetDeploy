from pydantic import BaseModel


class ImageRequest(BaseModel):
    bucket: str
    path: str