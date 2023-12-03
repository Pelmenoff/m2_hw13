from sqlalchemy import Column, String, Integer, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, validator
from datetime import date
from typing import List
from .database import Base
import secrets


class ContactCreate(BaseModel):
    """
    Pydantic model for creating a new contact.
    
    Attributes:
        first_name (str): The first name of the contact.
        last_name (str): The last name of the contact.
        email (EmailStr): The email address of the contact.
        phone_number (str): The phone number of the contact.
        birthday (date): The birthday of the contact.
        additional_data (str): Any additional data or notes for the contact.
    """
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_data: str


class ContactResponse(BaseModel):
    """
    Pydantic model for contact response data.
    
    Attributes:
        id (int): The unique identifier for the contact.
        first_name (str): The first name of the contact.
        last_name (str): The last name of the contact.
        email (EmailStr): The email address of the contact.
        phone_number (str): The phone number of the contact.
        birthday (date): The birthday of the contact.
        additional_data (str): Any additional data or notes for the contact.
    """
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
    """
    Pydantic model for a list of contact responses.
    
    Attributes:
        contacts (List[ContactResponse]): A list of contacts.
    """
    contacts: List[ContactResponse]

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    """
    Pydantic model for user creation.
    
    Attributes:
        email (EmailStr): The email address of the user.
        password (str): The password for the user account.

    Methods:
        validate_password: Validates that the password is at least 8 characters long.
    """
    email: EmailStr
    password: str

    @validator('password')
    def validate_password(cls, value):
        """
        Validates that the password is at least 8 characters long.

        :param value: The password to validate.
        :return: The validated password.
        :raises ValueError: If the password is shorter than 8 characters.
        """
        if len(value) < 8:
            raise ValueError('Password should be at least 8 characters long')
        return value

class UserResponse(BaseModel):
    """
    Pydantic model for user response data.
    
    Attributes:
        id (int): The unique identifier for the user.
        email (EmailStr): The email address of the user.
        is_verified (bool): Flag to indicate if the user's email address has been verified.
    """
    id: int
    email: str
    is_verified: bool

    class Config:
        from_attributes = True


class Contact(Base):
    """
    SQLAlchemy model for a contact.

    Attributes:
        id (int): The unique identifier for the contact.
        first_name (str): The first name of the contact.
        last_name (str): The last name of the contact.
        email (str): The email address of the contact.
        phone_number (str): The phone number of the contact.
        birthday (date): The birthday of the contact.
        additional_data (str): Any additional data or notes associated with the contact.

        owner_id (int): The unique identifier for the owner (user) of the contact.
        owner (relationship): The relationship to the user who owns this contact.
    """
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
    """
    SQLAlchemy model for a user.

    Attributes:
        id (int): The unique identifier for the user.
        email (str): The email address of the user.
        hashed_password (str): The hashed password for the user account.
        is_verified (bool): Flag to indicate if the user's email address has been verified.
        verification_token (str): A token used for verifying the user's email address.
        avatar_url (str): URL to the user's avatar image.

        contacts (relationship): A list of contacts associated with the user.

    Methods:
        generate_verification_token: Generates a unique verification token for the user's email address.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, unique=True, index=True)
    avatar_url = Column(String)
    contacts = relationship("Contact", back_populates="owner")

    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe()
