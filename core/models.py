import builtins
import datetime
import uuid

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Property(models.Model):

    PROPERTY_TYPE_CHOICES = [
        ('APARTMENT', 'Apartment'),
        ('HOUSE', 'House'),
        ('ROOM', 'Single Room'),
        ('SHARED', 'Shared Room'),
    ]

    FURNISHED_STATUS_CHOICES = [
        ('FURNISHED', 'Furnished'),
        ('SEMI', 'Semi-Furnished'),
        ('UNFURNISHED', 'Unfurnished'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='properties',
        help_text="Property owner user"
    )

    title = models.CharField(max_length=200, help_text="Property listing title")
    description = models.TextField(help_text="Detailed description of the property")
    location = models.CharField(max_length=100, help_text="City / Area / Locality")
    address = models.TextField(help_text="Full address of the property")

    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly rent amount in ₹"
    )
    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Security deposit amount in ₹"
    )

    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES,
        default='APARTMENT'
    )
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    furnished_status = models.CharField(
        max_length=20,
        choices=FURNISHED_STATUS_CHOICES,
        default='UNFURNISHED'
    )

    wifi_available = models.BooleanField(default=False, verbose_name="Wi-Fi Available")
    parking_available = models.BooleanField(default=False, verbose_name="Parking Available")
    other_amenities = models.TextField(
        blank=True,
        help_text="Other facilities (e.g. Gym, Power Backup, Elevator, Security)"
    )

    is_available = models.BooleanField(default=True, verbose_name="Available for Rent")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Property"
        verbose_name_plural = "Properties"

    def __str__(self):
        return f"{self.title} - {self.location} (₹{self.monthly_rent}/mo)"

    @property
    def main_image(self):
        """Returns the first image for display or None."""
        first_img = self.images.first()
        return first_img.image.url if first_img else None


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='property_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Image for {self.property.title}"


class RentalRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rental_requests',
        help_text="Tenant who submitted the rental request"
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='rental_requests',
        help_text="Requested rental property"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incoming_rental_requests',
        help_text="Property owner receiving the request"
    )

    requested_move_in_date = models.DateField(help_text="Tenant's intended move-in date")
    message = models.TextField(blank=True, help_text="Optional message from tenant to property owner")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Rental Request"
        verbose_name_plural = "Rental Requests"

    def __str__(self):
        return f"Request by {self.tenant.username} for {self.property.title} ({self.get_status_display()})"


class Tenancy(models.Model):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_COMPLETED = 'COMPLETED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenancies',
        help_text="Tenant renting the property"
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='tenancies',
        help_text="Rented property"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owner_tenancies',
        help_text="Property owner"
    )

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='tenancy',
        null=True,
        blank=True,
        help_text="Original rental request"
    )

    rental_start_date = models.DateField(help_text="Lease start date (move-in date)")
    rental_end_date = models.DateField(help_text="Lease agreement end date")

    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly rent amount in ₹"
    )
    rent_due_day = models.PositiveIntegerField(
        default=5,
        help_text="Rent due day of the month (1 to 28)"
    )
    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Security deposit amount in ₹"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Tenancy"
        verbose_name_plural = "Tenancies"

    def __str__(self):
        return f"Tenancy for {self.property.title} - Tenant: {self.tenant.username} ({self.get_status_display()})"

    @builtins.property
    def days_until_expiry(self):
        """Calculate remaining days until lease agreement expires."""
        today = datetime.date.today()
        return (self.rental_end_date - today).days

    @builtins.property
    def is_approaching_expiry(self):
        """Check if tenancy expires within 30 days."""
        days = self.days_until_expiry
        return 0 <= days <= 30


    def get_or_create_current_rent_record(self):
        """Helper to get or create the rent record for the current rental month if active & within lease period."""
        if self.status != Tenancy.STATUS_ACTIVE:
            return None

        today = datetime.date.today()
        rent_month = datetime.date(today.year, today.month, 1)

        # Calculate due date for current month using rent_due_day (max 28)
        due_day = min(self.rent_due_day, 28)
        try:
            due_date = datetime.date(today.year, today.month, due_day)
        except ValueError:
            due_date = datetime.date(today.year, today.month, 28)

        # Do not create rent obligation if due_date is before rental_start_date or after rental_end_date
        if due_date < self.rental_start_date or due_date > self.rental_end_date:
            return None

        rent_record, created = RentRecord.objects.get_or_create(
            tenancy=self,
            rent_month=rent_month,
            defaults={
                'amount': self.monthly_rent,
                'due_date': due_date,
            }
        )
        return rent_record


class RentRecord(models.Model):
    STATUS_UPCOMING = 'UPCOMING'
    STATUS_DUE = 'DUE'
    STATUS_PAID = 'PAID'
    STATUS_OVERDUE = 'OVERDUE'

    STATUS_CHOICES = [
        (STATUS_UPCOMING, 'Upcoming'),
        (STATUS_DUE, 'Due'),
        (STATUS_PAID, 'Paid'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    tenancy = models.ForeignKey(
        Tenancy,
        on_delete=models.CASCADE,
        related_name='rent_records',
        help_text="Associated tenancy lease"
    )

    rent_month = models.DateField(
        help_text="Rent month (stored as 1st day of month, e.g., 2026-10-01)"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly rent amount in ₹"
    )

    due_date = models.DateField(
        help_text="Rent payment due date"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UPCOMING
    )

    paid_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when payment was completed"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-rent_month']
        verbose_name = "Rent Record"
        verbose_name_plural = "Rent Records"
        constraints = [
            models.UniqueConstraint(
                fields=['tenancy', 'rent_month'],
                name='unique_tenancy_rent_month'
            )
        ]

    def __str__(self):
        return f"Rent for {self.tenancy.property.title} ({self.rent_month.strftime('%B %Y')}) - {self.get_computed_status()}"

    def get_computed_status(self):
        """Calculate dynamic payment status based on current date and paid_date."""
        if self.paid_date is not None or self.payment_status == self.STATUS_PAID:
            return self.STATUS_PAID

        today = datetime.date.today()
        if today < self.due_date:
            return self.STATUS_UPCOMING
        elif today == self.due_date:
            return self.STATUS_DUE
        else:
            return self.STATUS_OVERDUE

    def get_days_message(self):
        """Calculate user-friendly status message relative to current date."""
        if self.paid_date is not None or self.payment_status == self.STATUS_PAID:
            if self.paid_date:
                return f"Paid on {self.paid_date.strftime('%d %b %Y')}"
            return "Paid"

        today = datetime.date.today()
        diff = (self.due_date - today).days

        if diff > 0:
            return f"{diff} day{'s' if diff > 1 else ''} remaining"
        elif diff == 0:
            return "Rent is due today"
        else:
            return f"{abs(diff)} day{'s' if abs(diff) > 1 else ''} overdue"


def generate_transaction_id():
    """Generate unique demo transaction ID in format SR-YYYYMMDD-XXXXXXXX."""
    today_str = datetime.date.today().strftime('%Y%m%d')
    random_code = uuid.uuid4().hex[:8].upper()
    return f"SR-{today_str}-{random_code}"


class Payment(models.Model):
    PAYMENT_METHOD_UPI = 'UPI'
    PAYMENT_METHOD_CARD = 'CARD'
    PAYMENT_METHOD_NETBANKING = 'NETBANKING'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_UPI, 'UPI'),
        (PAYMENT_METHOD_CARD, 'Debit/Credit Card'),
        (PAYMENT_METHOD_NETBANKING, 'Net Banking'),
    ]

    rent_record = models.OneToOneField(
        RentRecord,
        on_delete=models.CASCADE,
        related_name='payment',
        help_text="Associated rent record"
    )

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Tenant who completed payment"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_payments',
        help_text="Property owner receiving payment"
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Property for which rent was paid"
    )

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount paid in ₹"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_UPI
    )

    transaction_id = models.CharField(
        max_length=50,
        unique=True,
        default=generate_transaction_id,
        help_text="Unique simulated transaction ID"
    )

    paid_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when payment was processed"
    )

    class Meta:
        ordering = ['-paid_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.transaction_id} - ₹{self.amount_paid} ({self.get_payment_method_display()})"

    @builtins.property
    def receipt_number(self):
        """Generate a unique human-readable receipt number (e.g., SR-RCP-2026-00001)."""
        year = self.paid_at.strftime('%Y') if self.paid_at else datetime.date.today().strftime('%Y')
        return f"SR-RCP-{year}-{self.pk:05d}"


class UtilityBill(models.Model):
    tenancy = models.ForeignKey(
        Tenancy,
        on_delete=models.CASCADE,
        related_name='utility_bills',
        help_text="Associated active tenancy lease"
    )

    billing_month = models.DateField(
        help_text="Billing month (stored as 1st day of month, e.g., 2026-09-01)"
    )

    electricity_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Electricity charge in ₹"
    )

    water_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Water charge in ₹"
    )

    maintenance_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Maintenance charge in ₹"
    )

    other_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Other charge in ₹"
    )

    note = models.TextField(
        blank=True,
        help_text="Optional note or breakdown details"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when record was created"
    )

    class Meta:
        ordering = ['-billing_month', '-created_at']
        verbose_name = "Utility Bill"
        verbose_name_plural = "Utility Bills"
        constraints = [
            models.UniqueConstraint(
                fields=['tenancy', 'billing_month'],
                name='unique_tenancy_utility_billing_month'
            )
        ]

    def __str__(self):
        return f"Utility Bill for {self.tenancy.property.title} ({self.billing_month.strftime('%B %Y')}) - ₹{self.total_utility_charges}"

    def clean(self):
        super().clean()
        for field in ['electricity_charge', 'water_charge', 'maintenance_charge', 'other_charge']:
            val = getattr(self, field)
            if val is not None and val < 0:
                raise ValidationError({field: "Charge amount must be zero or positive."})

    @builtins.property
    def total_utility_charges(self):
        """Calculate total utility charges (Electricity + Water + Maintenance + Other)."""
        return (self.electricity_charge or 0) + (self.water_charge or 0) + (self.maintenance_charge or 0) + (self.other_charge or 0)


class MaintenanceRequest(models.Model):
    CATEGORY_PLUMBING = 'PLUMBING'
    CATEGORY_ELECTRICAL = 'ELECTRICAL'
    CATEGORY_WATER = 'WATER'
    CATEGORY_FURNITURE = 'FURNITURE'
    CATEGORY_APPLIANCE = 'APPLIANCE'
    CATEGORY_OTHER = 'OTHER'

    CATEGORY_CHOICES = [
        (CATEGORY_PLUMBING, 'Plumbing'),
        (CATEGORY_ELECTRICAL, 'Electrical'),
        (CATEGORY_WATER, 'Water'),
        (CATEGORY_FURNITURE, 'Furniture'),
        (CATEGORY_APPLIANCE, 'Appliance'),
        (CATEGORY_OTHER, 'Other'),
    ]

    PRIORITY_LOW = 'LOW'
    PRIORITY_MEDIUM = 'MEDIUM'
    PRIORITY_HIGH = 'HIGH'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    tenancy = models.ForeignKey(
        Tenancy,
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
        help_text="Associated active tenancy"
    )

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
        help_text="Tenant submitting the request"
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OTHER
    )

    title = models.CharField(
        max_length=200,
        help_text="Short title describing the problem"
    )

    description = models.TextField(
        help_text="Detailed description of the maintenance issue"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM
    )

    photo = models.ImageField(
        upload_to='maintenance_photos/',
        blank=True,
        null=True,
        help_text="Optional photo of the problem"
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when request was submitted"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    owner_response = models.TextField(
        blank=True,
        help_text="Optional owner response, resolution note, or update"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when work was marked completed"
    )

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Maintenance Request"
        verbose_name_plural = "Maintenance Requests"

    def __str__(self):
        return f"{self.get_category_display()} Issue: {self.title} ({self.get_status_display()})"


class RenewalRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    tenancy = models.ForeignKey(
        Tenancy,
        on_delete=models.CASCADE,
        related_name='renewal_requests',
        help_text="Associated active tenancy lease"
    )

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='renewal_requests',
        help_text="Tenant requesting lease renewal"
    )

    requested_new_end_date = models.DateField(
        help_text="Tenant's requested new lease end date"
    )

    message = models.TextField(
        blank=True,
        help_text="Optional message from tenant to property owner"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    owner_response = models.TextField(
        blank=True,
        help_text="Optional response note from property owner"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when renewal request was submitted"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Renewal Request"
        verbose_name_plural = "Renewal Requests"

    def __str__(self):
        return f"Renewal Request for {self.tenancy.property.title} by {self.tenant.username} ({self.get_status_display()})"










