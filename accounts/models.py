from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_TENANT = 'TENANT'
    ROLE_OWNER = 'OWNER'

    ROLE_CHOICES = [
        (ROLE_TENANT, 'Tenant'),
        (ROLE_OWNER, 'Property Owner'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_TENANT,
        help_text="User role on SafeRent platform"
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )

    def is_tenant(self):
        return self.role == self.ROLE_TENANT

    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
