from __future__ import annotations

from pydantic import BaseModel


class Image(BaseModel):
    id: str | None
    title: str
    location: str | None = None
    date: str | None = None
    description: str | None = None
    description_generated: str | None = None
    tags: list[str] | None = None
