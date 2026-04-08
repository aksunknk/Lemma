from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from pydantic import BaseModel
from typing import Optional
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    # The 4 dimensions
    era = Column(Integer)
    origin_domestic = Column(Boolean)
    popularity = Column(Float)
    style_score = Column(Float)
    
    category = Column(String, nullable=True) # A, B, C, D

class BookSchema(BaseModel):
    id: str
    title: str
    author: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    era: int
    origin_domestic: bool
    popularity: float
    style_score: float

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    era_min: int = 1800
    era_max: int = 2024
    origin_domestic: bool
    popularity: float
    style_score: float
    keywords: Optional[str] = None
