from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("HR profile", {"fields": ("role", "department", "job_title")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("HR profile", {"fields": ("email", "role", "department", "job_title")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
