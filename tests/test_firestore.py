# CREATE: /tests/test_firestore.py
import pytest
from database.firestore import FirestoreClient
from unittest.mock import Mock, patch
from google.cloud.firestore import Client

@pytest.fixture
def firestore_client():
    with patch("google.cloud.firestore.Client") as mock_client:
        client = FirestoreClient()
        client.client = mock_client.return_value
        yield client

def test_get_user_exists(firestore_client):
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"name": "Test", "role": "user"}
    firestore_client.client.collection.return_value.document.return_value.get.return_value = mock_doc

    result = firestore_client.get_user("test_user")
    assert result == {"name": "Test", "role": "user"}
    firestore_client.client.collection.assert_called_with("users")

def test_get_user_not_exists(firestore_client):
    mock_doc = Mock()
    mock_doc.exists = False
    firestore_client.client.collection.return_value.document.return_value.get.return_value = mock_doc

    result = firestore_client.get_user("test_user")
    assert result is None

def test_save_user(firestore_client):
    firestore_client.save_user("test_user", {"name": "Test"})
    firestore_client.client.collection.return_value.document.return_value.set.assert_called_with({"name": "Test"}, merge=True)
