from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app, get_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import pytest

# Create a test database and override the get_db dependency
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency override function
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Setup and teardown functions for the database
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

# The actual test function
def test_register_user(db_session):
    with patch('main.FastMail.send_message') as mock_send:
        client = TestClient(app)
        response = client.post("/register/", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        assert response.status_code == 200
        assert response.json() == {"msg": "User created. Please check your email to verify your account."}
        mock_send.assert_called_once()

# Test for retrieving user's contacts
def test_get_contacts(db_session):
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        response = client.get("/contacts/")
        assert response.status_code == 200
        # Add additional assertions based on the expected response content

# Test for creating a new contact
def test_create_contact(db_session):
    with patch("main.get_db", return_value=db_session):
        test_contact_data = {
            "name": "John Doe",
            "birthday": "1990-01-01",
            "email": "john.doe@example.com",
        }
        client = TestClient(app)
        response = client.post("/contacts/", json=test_contact_data)
        assert response.status_code == 200
        # Verify that the contact was actually created, possibly by checking the database

# Test for updating a contact
def test_update_contact(db_session):
    contact_id = 1  # Assuming a contact with this ID exists in the test database
    with patch("main.get_db", return_value=db_session):
        updated_contact_data = {
            "name": "Jane Doe",
            "birthday": "1991-02-02",
            "email": "jane.doe@example.com",
        }
        client = TestClient(app)
        response = client.put(f"/contacts/{contact_id}", json=updated_contact_data)
        assert response.status_code == 200
        # Confirm that the contact was updated by checking the response or database

# Test for deleting a contact
def test_delete_contact(db_session):
    contact_id = 1  # Assuming a contact with this ID exists in the test database
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        response = client.delete(f"/contacts/{contact_id}")
        assert response.status_code == 200
        # Confirm that the contact was deleted, possibly by checking the database

# Test for searching contacts
def test_search_contacts(db_session):
    search_query = "John"  # Assuming this search term will yield results
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        response = client.get(f"/contacts/search?query={search_query}")
        assert response.status_code == 200
        # Add assertions to validate the search results are as expected

# Test for upcoming birthdays
def test_upcoming_birthdays(db_session):
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        response = client.get("/contacts/upcoming_birthdays")
        assert response.status_code == 200
        # Validate that the response contains contacts with upcoming birthdays

# Test for searching contacts by a query string
def test_search_contacts(db_session):
    search_query = "John"  # Assuming there are contacts with "John" in their name or email
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        response = client.get(f"/contacts/search/?q={search_query}")
        assert response.status_code == 200
        # Verify that the response contains contacts that match the search query

# Test for retrieving upcoming birthdays
def test_upcoming_birthdays(db_session):
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        response = client.get("/contacts/upcoming_birthdays/")
        assert response.status_code == 200
        # Verify that the response contains contacts with upcoming birthdays

# Test for user authentication
def test_authenticate_user(db_session):
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        auth_data = {
            "username": "user@example.com",
            "password": "password123"
        }
        response = client.post("/token", data=auth_data)
        assert response.status_code == 200
        # Verify that a valid token is returned for correct user credentials

# Test for user registration
def test_register_user(db_session):
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        user_data = {
            "email": "newuser@example.com",
            "password": "newpassword"
        }
        response = client.post("/register/", json=user_data)
        assert response.status_code == 200
        # Verify that the user was registered successfully

# Test for protected endpoint access without authentication
def test_protected_endpoint_unauthorized_access():
    client = TestClient(app)
    response = client.get("/protected/")
    assert response.status_code == 401
    # Verify that the endpoint is protected and returns an unauthorized error without a valid token

# Test for updating user profile information
def test_update_user_profile(db_session):
    user_id = 1  # Assuming a user with this ID exists in the test database
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        updated_user_data = {
            "name": "Alice Smith",
            "bio": "Loves coding and cats",
        }
        response = client.put(f"/users/{user_id}", json=updated_user_data)
        assert response.status_code == 200
        # Verify that the user profile was updated by checking the response or database

# Test for handling invalid user update attempts
def test_invalid_update_user_profile(db_session):
    user_id = 2  # Assuming this user ID does not have permission to update another user's data
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        invalid_user_data = {
            "name": "Bob Johnson",
            "bio": "Incorrect user data",
        }
        response = client.put(f"/users/{user_id}", json=invalid_user_data)
        assert response.status_code == 403
        # Verify that the server returns a forbidden status code for invalid update attempts

# Test for password reset functionality
def test_password_reset_request(db_session):
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        password_reset_request_data = {
            "email": "user@example.com",
        }
        response = client.post("/password-reset/", json=password_reset_request_data)
        assert response.status_code == 200
        # Verify that a password reset request is handled properly

# Test for actual password reset using token
def test_password_reset(db_session):
    reset_token = "valid-reset-token"  # Assuming this token is valid and linked to a user's password reset request
    with patch("main.get_db", return_value=db_session):
        client = TestClient(app)
        password_reset_data = {
            "token": reset_token,
            "new_password": "newsecurepassword",
        }
        response = client.post("/password-reset/confirm", json=password_reset_data)
        assert response.status_code == 200
        # Verify that the password is reset successfully when provided with a valid token