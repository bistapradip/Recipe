"""Test API user functionality - Public (unauthenticated) access"""

# Import Django's TestCase for writing tests
from django.test import TestCase
# Import method to retrieve the custom user model
from django.contrib.auth import get_user_model
# Import reverse to generate URLs from route names
from django.urls import reverse

# Import DRF's APIClient for making test requests
from rest_framework.test import APIClient
# Import DRF's status codes for cleaner assertions
from rest_framework import status

# Define the URL for user creation using the name defined in your URL config (e.g., 'user:create')
CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')

# Helper function to create a user with given parameters
def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


# Test class for public (unauthenticated) API user tests
class PublicUserApiTests(TestCase):
    """Test the users API (public access)"""

    # Setup runs before every individual test
    def setUp(self):
        # Create an APIClient instance to simulate HTTP requests
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""

        # Payload with valid user data
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': "Test_name"
        }

        # Make POST request to create the user
        res = self.client.post(CREATE_USER_URL, payload)

        # Check that the response status is HTTP 201 Created
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Fetch the user from the database to verify creation
        user = get_user_model().objects.get(email=payload['email'])

        # Verify the password is correctly hashed and saved
        self.assertTrue(user.check_password(payload['password']))

        # Make sure the password is not returned in the response data
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with email already exists"""

        # Payload with valid user data
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test_Name',
        }

        # Create the user once
        create_user(**payload)

        # Try creating the same user again via API
        res = self.client.post(CREATE_USER_URL, payload)

        # Expect a 400 Bad Request error since the email is already taken
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test error returned if password is too short"""

        # Payload with a short password (less than 8 chars)
        payload = {
            'email': "test@example.com",
            'password': 'pw',
            'name': 'Test_name',
        }

        # Try creating the user with short password
        res = self.client.post(CREATE_USER_URL, payload)

        # Expect 400 Bad Request due to password validation failure
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Check that no user was created with that email
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()

        # Assert user does not exist in DB
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generate token for valid credentials"""
        user_details = {
            'name': 'Test_name',
            'email': 'test@example.com',
            'password': 'test-user-password123',
        }

        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password'],
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test returns error if credentials is invalid"""

        create_user(email = "test@example.com", password='goodpass')

        payload = {'email': 'test@example.com', 'password': 'badpass'}
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Test posting a blank pasword throw error"""

        payload = {'email':'test@example.com','password': ''}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reterive_user_unauthorized(self):
        """Test authentication is required"""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test api requests that require authentication"""

    def setUp(self):
        self.user = create_user(
            email = "test@example.com",
            password = "testapi123",
            name = "Test Name",
        )

        self.client = APIClient()
        self.client.force_authenticate(user = self.user)


    def test_retrieve_profile_success(self):
        """Test Retrieving profile for logged in user"""

        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,

        })


    def test_post_me_not_allowed(self):
        """Test Post is not allowed for the me endpoint"""

        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test U[dating the profile of authenticated user"""
        payload = {'name': 'Updated name', 'password': 'newpassword123'}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

