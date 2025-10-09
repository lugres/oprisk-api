"""
Tests for the user API.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse("users:create")


def create_user(**params):
    """Create and return a new user (helper function)."""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features of the user API."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful."""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test name",
        }
        # attempting to create a user via POST
        res = self.client.post(CREATE_USER_URL, payload)

        # asserting user was created successfully
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # getting a newly created user via GET
        user = get_user_model().objects.get(email=payload["email"])
        # check that the passwords match
        self.assertTrue(user.check_password(payload["password"]))
        # check that password hash is not returned in the response
        self.assertNotIn("password", res.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with email exists."""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        }
        create_user(**payload)
        # attempting to create the same user again via POST
        res = self.client.post(CREATE_USER_URL, payload)

        # check that the error was received back from the API
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test an error is returned if password is less than 5 chars."""
        payload = {
            "email": "test@example.com",
            "password": "psw",
            "name": "Test User",
        }
        # attempting to create a user with a too short password via POST
        res = self.client.post(CREATE_USER_URL, payload)

        # check that the error was received back from the API
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # check whether the user exists by querying database
        user_exists = (
            get_user_model()
            .objects.filter(
                email=payload["email"],
            )
            .exists()
        )
        self.assertFalse(user_exists)
