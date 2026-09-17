import datetime
from django import forms
from django.core.exceptions import ValidationError
from .models import Property, RentalRequest, Tenancy, UtilityBill, MaintenanceRequest, RenewalRequest

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class PropertyForm(forms.ModelForm):
    photos = MultipleFileField(
        required=False,
        help_text="Upload property photos (select multiple images)"
    )

    class Meta:
        model = Property
        fields = [
            'title',
            'description',
            'location',
            'address',
            'monthly_rent',
            'security_deposit',
            'property_type',
            'bedrooms',
            'bathrooms',
            'furnished_status',
            'wifi_available',
            'parking_available',
            'other_amenities',
            'is_available',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Spacious 2 BHK Apartment near Tech Park'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe property highlights, nearby spots, rules, etc.'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Indiranagar, Bengaluru'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Full street address & door number'
            }),
            'monthly_rent': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '25000',
                'min': '0',
                'step': '500'
            }),
            'security_deposit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '50000',
                'min': '0',
                'step': '1000'
            }),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'furnished_status': forms.Select(attrs={'class': 'form-select'}),
            'wifi_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parking_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'other_amenities': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'e.g. 24/7 Power Backup, Gym, Elevator, Swimming Pool'
            }),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_monthly_rent(self):
        monthly_rent = self.cleaned_data.get('monthly_rent')
        if monthly_rent is not None and monthly_rent < 0:
            raise ValidationError("Monthly rent cannot be a negative value.")
        return monthly_rent

    def clean_security_deposit(self):
        security_deposit = self.cleaned_data.get('security_deposit')
        if security_deposit is not None and security_deposit < 0:
            raise ValidationError("Security deposit cannot be a negative value.")
        return security_deposit


class RentalRequestForm(forms.ModelForm):
    requested_move_in_date = forms.DateField(
        label="Requested Move-in Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
    )
    message = forms.CharField(
        label="Message to Property Owner (Optional)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Introduce yourself, specify occupancy details, or ask any questions...'
        }),
        required=False
    )

    class Meta:
        model = RentalRequest
        fields = ['requested_move_in_date', 'message']

    def clean_requested_move_in_date(self):
        move_in_date = self.cleaned_data.get('requested_move_in_date')
        if move_in_date and move_in_date < datetime.date.today():
            raise ValidationError("Move-in date cannot be in the past. Please select a valid future date.")
        return move_in_date


class TenancyAcceptForm(forms.ModelForm):
    rental_start_date = forms.DateField(
        label="Rental Start Date (Move-in Date)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    rental_end_date = forms.DateField(
        label="Rental End Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    monthly_rent = forms.DecimalField(
        label="Monthly Rent (₹)",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '100'}),
        required=True
    )
    rent_due_day = forms.IntegerField(
        label="Rent Due Day of Month (1 - 28)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '28'}),
        required=True
    )
    security_deposit = forms.DecimalField(
        label="Security Deposit (₹)",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '100'}),
        required=True
    )

    class Meta:
        model = Tenancy
        fields = ['rental_start_date', 'rental_end_date', 'monthly_rent', 'rent_due_day', 'security_deposit']

    def clean_rent_due_day(self):
        due_day = self.cleaned_data.get('rent_due_day')
        if due_day is not None and (due_day < 1 or due_day > 28):
            raise ValidationError("Rent due day must be between 1 and 28.")
        return due_day

    def clean_monthly_rent(self):
        rent = self.cleaned_data.get('monthly_rent')
        if rent is not None and rent < 0:
            raise ValidationError("Monthly rent cannot be negative.")
        return rent

    def clean_security_deposit(self):
        deposit = self.cleaned_data.get('security_deposit')
        if deposit is not None and deposit < 0:
            raise ValidationError("Security deposit cannot be negative.")
        return deposit

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('rental_start_date')
        end_date = cleaned_data.get('rental_end_date')

        if start_date and end_date:
            if end_date <= start_date:
                self.add_error('rental_end_date', "Rental end date must be after the start date.")

        return cleaned_data


class MonthDateField(forms.DateField):
    """Custom DateField to accept YYYY-MM HTML5 month inputs and normalize to 1st of month."""
    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, datetime.date):
            return datetime.date(value.year, value.month, 1)
        if isinstance(value, str):
            value = value.strip()
            if len(value) == 7 and '-' in value:
                try:
                    year, month = map(int, value.split('-'))
                    return datetime.date(year, month, 1)
                except ValueError:
                    pass
        return super().to_python(value)


class UtilityBillForm(forms.ModelForm):
    billing_month = MonthDateField(
        label="Billing Month",
        widget=forms.DateInput(attrs={
            'type': 'month',
            'class': 'form-control'
        }),
        help_text="Select billing month"
    )
    electricity_charge = forms.DecimalField(
        label="Electricity Charge (₹)",
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control charge-input', 'min': '0', 'step': '1'}),
        required=True
    )
    water_charge = forms.DecimalField(
        label="Water Charge (₹)",
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control charge-input', 'min': '0', 'step': '1'}),
        required=True
    )
    maintenance_charge = forms.DecimalField(
        label="Maintenance Charge (₹)",
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control charge-input', 'min': '0', 'step': '1'}),
        required=True
    )
    other_charge = forms.DecimalField(
        label="Other Charge (₹)",
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control charge-input', 'min': '0', 'step': '1'}),
        required=True
    )
    note = forms.CharField(
        label="Note (Optional)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add optional notes or breakdown details for tenant...'
        }),
        required=False
    )

    class Meta:
        model = UtilityBill
        fields = ['tenancy', 'billing_month', 'electricity_charge', 'water_charge', 'maintenance_charge', 'other_charge', 'note']

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if owner:
            self.fields['tenancy'].queryset = Tenancy.objects.filter(
                owner=owner,
                status=Tenancy.STATUS_ACTIVE
            ).select_related('property', 'tenant')
            self.fields['tenancy'].widget.attrs.update({'class': 'form-select'})
            self.fields['tenancy'].label_from_instance = lambda obj: f"{obj.property.title} — Tenant: {obj.tenant.get_full_name() or obj.tenant.username}"

    def clean_electricity_charge(self):
        val = self.cleaned_data.get('electricity_charge')
        if val is not None and val < 0:
            raise ValidationError("Electricity charge cannot be negative.")
        return val

    def clean_water_charge(self):
        val = self.cleaned_data.get('water_charge')
        if val is not None and val < 0:
            raise ValidationError("Water charge cannot be negative.")
        return val

    def clean_maintenance_charge(self):
        val = self.cleaned_data.get('maintenance_charge')
        if val is not None and val < 0:
            raise ValidationError("Maintenance charge cannot be negative.")
        return val

    def clean_other_charge(self):
        val = self.cleaned_data.get('other_charge')
        if val is not None and val < 0:
            raise ValidationError("Other charge cannot be negative.")
        return val

    def clean(self):
        cleaned_data = super().clean()
        tenancy = cleaned_data.get('tenancy')
        billing_month = cleaned_data.get('billing_month')

        if tenancy and billing_month:
            query = UtilityBill.objects.filter(tenancy=tenancy, billing_month=billing_month)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise ValidationError(f"A utility bill for this tenancy ({tenancy.property.title}) for {billing_month.strftime('%B %Y')} already exists.")
        return cleaned_data


class MaintenanceRequestForm(forms.ModelForm):
    category = forms.ChoiceField(
        choices=MaintenanceRequest.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Problem Category"
    )
    title = forms.CharField(
        label="Problem Title",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Water leakage in bathroom sink'
        })
    )
    description = forms.CharField(
        label="Problem Description",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide details about when the issue started, exact location, symptoms...'
        })
    )
    priority = forms.ChoiceField(
        choices=MaintenanceRequest.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=MaintenanceRequest.PRIORITY_MEDIUM,
        label="Priority Level"
    )
    photo = forms.ImageField(
        label="Optional Photo Upload",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        required=False,
        help_text="Upload a photo showing the maintenance problem (optional)"
    )

    class Meta:
        model = MaintenanceRequest
        fields = ['category', 'title', 'description', 'priority', 'photo']


class MaintenanceUpdateForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=MaintenanceRequest.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Request Status"
    )
    owner_response = forms.CharField(
        label="Owner Response / Resolution Note (Optional)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Add updates for tenant, plumber arrival time, or resolution details...'
        }),
        required=False
    )

    class Meta:
        model = MaintenanceRequest
        fields = ['status', 'owner_response']


class RenewalRequestForm(forms.ModelForm):
    requested_new_end_date = forms.DateField(
        label="Requested New Agreement End Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=True
    )
    message = forms.CharField(
        label="Optional Message to Landlord",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why you are requesting a lease extension or specify terms...'
        }),
        required=False
    )

    class Meta:
        model = RenewalRequest
        fields = ['requested_new_end_date', 'message']

    def __init__(self, tenancy=None, *args, **kwargs):
        self.tenancy = tenancy
        super().__init__(*args, **kwargs)

    def clean_requested_new_end_date(self):
        new_date = self.cleaned_data.get('requested_new_end_date')
        if self.tenancy and new_date:
            if new_date <= self.tenancy.rental_end_date:
                raise ValidationError(
                    f"The requested new end date must be later than your current agreement end date ({self.tenancy.rental_end_date.strftime('%b %d, %Y')})."
                )
        return new_date





