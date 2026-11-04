"""API serializers for requisition data."""

from decimal import Decimal

from rest_framework import serializers

from accounts.models import User, UserRole
from .models import Requisition


class RequisitionSerializer(serializers.ModelSerializer):
    created_by = serializers.IntegerField(source="created_by_id", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    hiring_manager = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=UserRole.HIRING_MANAGER),
        required=False,
        allow_null=True,
    )
    hiring_manager_name = serializers.SerializerMethodField()
    required_skills = serializers.ListField(
        child=serializers.CharField(max_length=80, trim_whitespace=True),
        required=False,
        allow_empty=True,
        max_length=50,
    )
    minimum_experience_years = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=0,
        required=False, default=Decimal("0.0"),
    )
    salary_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    headcount = serializers.IntegerField(min_value=1, required=False, default=1)

    class Meta:
        model = Requisition
        fields = (
            "id", "reference_code", "title", "department", "location",
            "employment_type", "work_mode", "description", "responsibilities",
            "required_skills", "minimum_experience_years", "education_requirements",
            "salary_min", "salary_max", "currency", "headcount", "status",
            "created_by", "created_by_name", "hiring_manager", "hiring_manager_name",
            "target_close_date", "opened_at", "closed_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "reference_code", "created_by", "created_by_name",
            "hiring_manager_name", "opened_at", "closed_at", "created_at", "updated_at",
        )

    @staticmethod
    def get_created_by_name(obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    @staticmethod
    def get_hiring_manager_name(obj):
        if not obj.hiring_manager:
            return None
        return obj.hiring_manager.get_full_name() or obj.hiring_manager.username

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Enter a valid three-letter currency code.")
        return value

    def validate_required_skills(self, value):
        cleaned = [skill.strip() for skill in value]
        if any(not skill for skill in cleaned):
            raise serializers.ValidationError("Skills cannot be blank.")
        if len({skill.casefold() for skill in cleaned}) != len(cleaned):
            raise serializers.ValidationError("Required skills must not contain duplicates.")
        return cleaned

    def validate(self, attrs):
        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError(
                {"salary_max": "Salary maximum must be greater than or equal to salary minimum."}
            )
        return attrs
