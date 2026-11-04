from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from .models import Requisition, RequisitionStatus


class RequisitionAPITests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(
            username="recruiter", email="recruiter@example.test",
            password="Strong-Test-Password-123!", role=UserRole.RECRUITER,
        )
        self.manager = User.objects.create_user(
            username="manager", email="manager@example.test",
            password="Strong-Test-Password-123!", role=UserRole.HIRING_MANAGER,
        )
        self.other_manager = User.objects.create_user(
            username="manager2", email="manager2@example.test",
            password="Strong-Test-Password-123!", role=UserRole.HIRING_MANAGER,
        )
        self.admin = User.objects.create_user(
            username="hradmin", email="hradmin@example.test",
            password="Strong-Test-Password-123!", role=UserRole.ADMIN,
        )
        self.list_url = reverse("requisitions:requisition-list")
        self.payload = {
            "title": "Senior Controls Engineer",
            "department": "Engineering",
            "location": "Lahore, Pakistan",
            "employment_type": "FULL_TIME",
            "work_mode": "HYBRID",
            "description": "Design, develop and support industrial control systems.",
            "responsibilities": "Own PLC and SCADA engineering deliverables.",
            "required_skills": ["PLC", "SCADA", "FAT"],
            "minimum_experience_years": "5.0",
            "education_requirements": "Bachelor's degree in Engineering.",
            "salary_min": "200000.00",
            "salary_max": "350000.00",
            "currency": "PKR",
            "headcount": 1,
            "status": "DRAFT",
            "hiring_manager": self.manager.id,
            "target_close_date": "2026-12-31",
        }

    def create_requisition(self, **overrides):
        values = {**self.payload, **overrides}
        return Requisition.objects.create(
            title=values["title"],
            department=values["department"],
            description=values["description"],
            created_by=self.recruiter,
            hiring_manager=values.get("hiring_manager") and User.objects.get(
                id=values["hiring_manager"]
            ),
            status=values.get("status", RequisitionStatus.DRAFT),
        )

    def test_anonymous_user_cannot_list_requisitions(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_recruiter_can_create_requisition_and_creator_is_server_assigned(self):
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        requisition = Requisition.objects.get()
        self.assertEqual(requisition.created_by, self.recruiter)
        self.assertEqual(requisition.hiring_manager, self.manager)
        self.assertEqual(requisition.status, RequisitionStatus.DRAFT)
        self.assertTrue(response.data["reference_code"])

    def test_hiring_manager_sees_only_assigned_requisitions(self):
        assigned = self.create_requisition()
        other = self.create_requisition(
            title="Automation Engineer", hiring_manager=self.other_manager.id
        )
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_codes = {item["reference_code"] for item in response.data["results"]}
        self.assertEqual(result_codes, {str(assigned.reference_code)})
        detail = self.client.get(
            reverse("requisitions:requisition-detail", args=[other.reference_code])
        )
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_hiring_manager_cannot_create_or_edit_requisitions(self):
        requisition = self.create_requisition()
        self.client.force_authenticate(user=self.manager)
        create_response = self.client.post(self.list_url, self.payload, format="json")
        update_response = self.client.patch(
            reverse("requisitions:requisition-detail", args=[requisition.reference_code]),
            {"title": "Changed title"}, format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recruiter_can_open_a_draft_and_system_sets_opened_at(self):
        requisition = self.create_requisition()
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.patch(
            reverse("requisitions:requisition-detail", args=[requisition.reference_code]),
            {"status": "OPEN"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        requisition.refresh_from_db()
        self.assertIsNotNone(requisition.opened_at)
        self.assertEqual(requisition.status, RequisitionStatus.OPEN)

    def test_closed_requisition_cannot_be_reopened(self):
        requisition = self.create_requisition(status=RequisitionStatus.CLOSED)
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.patch(
            reverse("requisitions:requisition-detail", args=[requisition.reference_code]),
            {"status": "OPEN"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_salary_minimum_cannot_exceed_maximum(self):
        self.client.force_authenticate(user=self.recruiter)
        payload = {**self.payload, "salary_min": "400000.00", "salary_max": "300000.00"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("salary_max", response.data)

    def test_status_and_department_filters_work(self):
        self.create_requisition(status=RequisitionStatus.DRAFT)
        self.create_requisition(
            title="Automation Engineer",
            status=RequisitionStatus.OPEN,
            hiring_manager=self.manager.id,
        )
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get(self.list_url, {"status": "OPEN", "department": "Engineering"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Automation Engineer")

    def test_only_draft_requisitions_can_be_deleted(self):
        draft = self.create_requisition()
        opened = self.create_requisition(
            title="Open role", status=RequisitionStatus.OPEN,
        )
        self.client.force_authenticate(user=self.recruiter)
        draft_response = self.client.delete(
            reverse("requisitions:requisition-detail", args=[draft.reference_code])
        )
        opened_response = self.client.delete(
            reverse("requisitions:requisition-detail", args=[opened.reference_code])
        )
        self.assertEqual(draft_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(opened_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hr_admin_can_access_all_requisitions(self):
        assigned_to_other = self.create_requisition(hiring_manager=self.other_manager.id)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            reverse("requisitions:requisition-detail", args=[assigned_to_other.reference_code])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
