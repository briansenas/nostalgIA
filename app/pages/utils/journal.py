from __future__ import annotations

from pydantic import BaseModel


class Image(BaseModel):
    id: str | None
    title: str
    base64: str
    image_vector: list[float]
    location: str | None = None
    date: str | None = None
    description: str | None = None
    description_embedding: list[float] | None = None
    generated_description: str | None = None
    generated_description_embedding: list[float] | None = None
    tags: list[str] | None = None
