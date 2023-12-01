from sqlalchemy import Column, String, Integer, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, validator
from datetime import date
from .database import Base
from typing import List
import secrets


class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_data: str


class ContactResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_data: str

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    contacts: List[ContactResponse]

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator('password')
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError('Password should be at least 8 characters long')
        return value

class UserResponse(BaseModel):
    id: int
    email: str
    is_verified: bool

    class Config:
        from_attributes = True


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, index=True, unique=True)
    phone_number = Column(String, index=True)
    birthday = Column(Date)
    additional_data = Column(String)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="contacts")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, unique=True, index=True)
    contacts = relationship("Contact", back_populates="owner")

    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe()
