from sqlalchemy.orm import Session
from sqlalchemy import or_
from .models import Contact, User, ContactCreate
from datetime import datetime, timedelta


def create_contact(db: Session, contact: ContactCreate, current_user: User) -> Contact:
    """
    Create a new contact in the database.

    Args:
        db (Session): The database session.
        contact (ContactCreate): The contact information from the request.
        current_user (User): The user creating the contact.

    Returns:
        Contact: The newly created Contact object.
    """
    db_contact = Contact(**contact.dict(), owner_id=current_user.id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def get_contacts(db: Session, skip: int = 0, limit: int = 10):
    """
    Retrieve a list of contacts from the database.

    Args:
        db (Session): The database session.
        skip (int): The number of records to skip (for pagination).
        limit (int): The maximum number of records to return.

    Returns:
        List[Contact]: A list of Contact objects.
    """
    return db.query(Contact).offset(skip).limit(limit).all()


def get_contact_by_id(db: Session, contact_id: int):
    """
    Retrieve a single contact by its ID.

    Args:
        db (Session): The database session.
        contact_id (int): The ID of the contact to retrieve.

    Returns:
        Contact: The Contact object if found, else None.
    """
    return db.query(Contact).filter(Contact.id == contact_id).first()


def update_contact(
    db: Session, contact_id: int, contact_data: ContactCreate
) -> Contact:
    """
    Update an existing contact's information.

    Args:
        db (Session): The database session.
        contact_id (int): The ID of the contact to update.
        contact_data (ContactCreate): An object containing the updated contact details.

    Returns:
        Contact: The updated Contact object.
    """
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
    """
    Delete a contact from the database.

    Args:
        db (Session): The database session.
        contact_id (int): The ID of the contact to delete.

    Returns:
        None
    """
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    db.delete(db_contact)
    db.commit()


def search_contacts(db: Session, query: str, skip: int = 0, limit: int = 10):
    """
    Search for contacts by a query string.

    Args:
        db (Session): The database session.
        query (str): The search query string.
        skip (int): Number of records to skip (for pagination).
        limit (int): Max number of records to return.

    Returns:
        List[Contact]: A list of contacts that match the query.
    """
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
    """
    Retrieve contacts with upcoming birthdays within the next week.

    Args:
        db (Session): The database session.

    Returns:
        List[Contact]: A list of contacts with upcoming birthdays.
    """
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    return db.query(Contact).filter(Contact.birthday.between(today, next_week)).all()


def create_user(db: Session, email: str, hashed_password: str):
    """
    Create a new user in the database.

    Args:
        db (Session): The database session.
        email (str): The email address of the user.
        hashed_password (str): The hashed password for the user.

    Returns:
        User: The newly created User object.
    """
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    """
    Retrieve a user by their email address.

    Args:
        db (Session): The database session.
        email (str): The email address to search for.

    Returns:
        User: The User object if found, else None.
    """
    return db.query(User).filter(User.email == email).first()

def verify_user(db: Session, user_id: int):
    """
    Verify a user's account by setting their 'is_verified' status to True.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to verify.

    Returns:
        User: The verified User object if found, else None.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.is_verified = True
        db.commit()
        db.refresh(db_user)
    return db_user