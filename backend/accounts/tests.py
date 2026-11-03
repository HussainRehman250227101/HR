from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import User, UserRole


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recruiter1",
            email="recruiter@example.test",
            password="Strong-Test-Password-123!",
            role=UserRole.RECRUITER,
            first_name="Test",
            last_name="Recruiter",
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("accounts:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_obtain_jwt_pair(self):
        response = self.client.post(
            reverse("accounts:token_obtain_pair"),
            {"username": "recruiter1", "password": "Strong-Test-Password-123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_authenticated_user_can_read_own_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("accounts:me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["role"], UserRole.RECRUITER)
        self.assertEqual(response.data["email"], self.user.email)

    def test_refresh_token_endpoint(self):
        token_response = self.client.post(
            reverse("accounts:token_obtain_pair"),
            {"username": "recruiter1", "password": "Strong-Test-Password-123!"},
            format="json",
        )
        response = self.client.post(
            reverse("accounts:token_refresh"),
            {"refresh": token_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
