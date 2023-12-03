from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from main import app
from project import crud

client = TestClient(app)

@pytest.fixture
def mock_get_contacts():
    crud.get_contacts = Mock()
    crud.get_contacts.return_value = [
        {"id": 1, "name": "Alice", "phone_number": "1234567890"},
        {"id": 2, "name": "Bob", "phone_number": "0987654321"}
    ]
    return crud.get_contacts

def test_get_all_contacts(mock_get_contacts):
    response = client.get("/contacts/?skip=0&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert 'contacts' in data
    contacts = data['contacts']
    assert isinstance(contacts, list)
    assert len(contacts) == 2
    assert contacts[0]['name'] == "Alice"
    assert contacts[1]['name'] == "Bob"

    mock_get_contacts.assert_called_once_with(Mock(), skip=0, limit=10)
