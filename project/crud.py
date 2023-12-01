from sqlalchemy.orm import Session
from sqlalchemy import or_
from .models import Contact, User, ContactCreate
from datetime import datetime, timedelta


def create_contact(db: Session, contact: ContactCreate, current_user: User) -> Contact:
    db_contact = Contact(**contact.dict(), owner_id=current_user.id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def get_contacts(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Contact).offset(skip).limit(limit).all()


def get_contact_by_id(db: Session, contact_id: int):
    return db.query(Contact).filter(Contact.id == contact_id).first()


def update_contact(
    db: Session, contact_id: int, contact_data: ContactCreate
) -> Contact:
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    db_contact.first_name = contact_data.first_name
    db_contact.last_name = contact_data.last_name
    db_contact.email = contact_data.email
    db_contact.phone_number = contact_data.phone_number
    db_contact.birthday = contact_data.birthday
    db_contact.additional_data = contact_data.additional_data
    db.commit()
    db.refresh(db_contact)
    return db_contact


def delete_contact(db: Session, contact_id: int):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    db.delete(db_contact)
    db.commit()


def search_contacts(db: Session, query: str, skip: int = 0, limit: int = 10):
    return (
        db.query(Contact)
        .filter(
            or_(
                Contact.first_name.ilike(f"%{query}%"),
                Contact.last_name.ilike(f"%{query}%"),
                Contact.email.ilike(f"%{query}%"),
            )
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def upcoming_birthdays(db: Session):
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    return db.query(Contact).filter(Contact.birthday.between(today, next_week)).all()


def create_user(db: Session, email: str, hashed_password: str):
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def verify_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.is_verified = True
        db.commit()
        db.refresh(db_user)
    return db_user