from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from .models import Property, PropertyImage, RentalRequest, Tenancy, RentRecord, Payment, UtilityBill, MaintenanceRequest, RenewalRequest, generate_transaction_id
from .forms import PropertyForm, RentalRequestForm, TenancyAcceptForm, UtilityBillForm, MaintenanceRequestForm, MaintenanceUpdateForm, RenewalRequestForm

User = get_user_model()



def owner_required(view_func):
    """Decorator to ensure only logged-in Property Owners can access owner-only views."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != User.ROLE_OWNER and not request.user.is_superuser:
            messages.warning(request, "Access denied. Property management is restricted to Property Owners.")
            return redirect('accounts:tenant_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view



def home(request):
    """Render SafeRent platform homepage with featured available properties."""
    featured_properties = Property.objects.filter(is_available=True).order_by('-created_at')[:6]
    return render(request, 'core/home.html', {
        'featured_properties': featured_properties
    })


def properties(request):
    """Render SafeRent public properties listing page with search filters."""
    # Always restrict to available properties
    queryset = Property.objects.filter(is_available=True).order_by('-created_at')

    # Get search parameters
    location = request.GET.get('location', '').strip()
    min_rent = request.GET.get('min_rent', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    rent_range = request.GET.get('rent_range', '').strip()
    property_type = request.GET.get('property_type', '').strip()
    furnished_status = request.GET.get('furnished_status', '').strip()
    wifi_available = request.GET.get('wifi_available', '').strip()
    parking_available = request.GET.get('parking_available', '').strip()

    # Handle homepage preset rent range if min/max rent not explicitly set
    if rent_range and not min_rent and not max_rent:
        if rent_range == '1':
            max_rent = '5000'
        elif rent_range == '2':
            min_rent = '5000'
            max_rent = '10000'
        elif rent_range == '3':
            min_rent = '10000'
            max_rent = '20000'
        elif rent_range == '4':
            min_rent = '20000'

    # Filter 1: Location (partial & case-insensitive match)
    if location:
        queryset = queryset.filter(
            Q(location__icontains=location) |
            Q(title__icontains=location) |
            Q(address__icontains=location)
        )

    # Filter 2: Min Rent
    if min_rent:
        try:
            val = float(min_rent)
            if val >= 0:
                queryset = queryset.filter(monthly_rent__gte=val)
        except ValueError:
            pass

    # Filter 3: Max Rent
    if max_rent:
        try:
            val = float(max_rent)
            if val >= 0:
                queryset = queryset.filter(monthly_rent__lte=val)
        except ValueError:
            pass

    # Filter 4: Property Type
    if property_type and property_type != 'ALL':
        queryset = queryset.filter(property_type__iexact=property_type)

    # Filter 5: Furnished Status
    if furnished_status and furnished_status != 'ALL':
        queryset = queryset.filter(furnished_status__iexact=furnished_status)

    # Filter 6: Wi-Fi Availability
    is_wifi = wifi_available in ['true', 'True', '1', 'on']
    if is_wifi:
        queryset = queryset.filter(wifi_available=True)

    # Filter 7: Parking Availability
    is_parking = parking_available in ['true', 'True', '1', 'on']
    if is_parking:
        queryset = queryset.filter(parking_available=True)

    # Determine if any filters were actively applied
    has_active_filters = bool(location or min_rent or max_rent or rent_range or (property_type and property_type != 'ALL') or (furnished_status and furnished_status != 'ALL') or is_wifi or is_parking)

    return render(request, 'core/properties.html', {
        'properties': queryset,
        'has_active_filters': has_active_filters,
        'filters': {
            'location': location,
            'min_rent': min_rent,
            'max_rent': max_rent,
            'rent_range': rent_range,
            'property_type': property_type,
            'furnished_status': furnished_status,
            'wifi_available': is_wifi,
            'parking_available': is_parking,
        },
        'property_types': Property.PROPERTY_TYPE_CHOICES,
        'furnished_statuses': Property.FURNISHED_STATUS_CHOICES,
    })



def public_property_detail(request, pk):
    """Render public detail view for any property."""
    property_obj = get_object_or_404(Property, pk=pk)
    return render(request, 'core/public_property_detail.html', {
        'property': property_obj
    })


def how_it_works(request):
    """Render How SafeRent Works explanation page."""
    return render(request, 'core/how_it_works.html')



def about(request):
    """Render About SafeRent & SDG alignment page."""
    return render(request, 'core/about.html')


@owner_required
def add_property(request):
    """Add a new property listing (Owner Only)."""
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.owner = request.user
            property_obj.save()

            # Handle photo uploads
            photos = request.FILES.getlist('photos')
            for photo in photos:
                PropertyImage.objects.create(property=property_obj, image=photo)

            messages.success(request, f"Property '{property_obj.title}' listed successfully!")
            return redirect('core:my_properties')
        else:
            messages.error(request, "Please correct the errors in the property form below.")
    else:
        form = PropertyForm()

    return render(request, 'core/add_property.html', {'form': form})


@owner_required
def my_properties(request):
    """List all properties belonging to the logged-in property owner."""
    user_properties = Property.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'core/my_properties.html', {'properties': user_properties})


@owner_required
def property_detail(request, pk):
    """View detailed information about a property owned by the user."""
    property_obj = get_object_or_404(Property, pk=pk)
    
    # Ownership Check
    if property_obj.owner != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only view your own property listings.")
        return redirect('core:my_properties')

    return render(request, 'core/property_detail.html', {'property': property_obj})


@owner_required
def edit_property(request, pk):
    """Edit an existing property (Owner Only & Ownership Check)."""
    property_obj = get_object_or_404(Property, pk=pk)

    # Backend Ownership Check
    if property_obj.owner != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only edit your own properties.")
        return redirect('core:my_properties')

    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        if form.is_valid():
            form.save()

            # Handle new photo uploads if added during edit
            photos = request.FILES.getlist('photos')
            for photo in photos:
                PropertyImage.objects.create(property=property_obj, image=photo)

            messages.success(request, f"Property '{property_obj.title}' updated successfully.")
            return redirect('core:property_detail', pk=property_obj.pk)
        else:
            messages.error(request, "Please correct the errors in the property form.")
    else:
        form = PropertyForm(instance=property_obj)

    return render(request, 'core/edit_property.html', {
        'form': form,
        'property': property_obj
    })


@owner_required
def delete_property(request, pk):
    """Delete a property (Owner Only & Ownership Check)."""
    property_obj = get_object_or_404(Property, pk=pk)

    # Backend Ownership Check
    if property_obj.owner != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only delete your own properties.")
        return redirect('core:my_properties')

    if request.method == 'POST':
        title = property_obj.title
        property_obj.delete()
        messages.success(request, f"Property '{title}' has been deleted successfully.")
        return redirect('core:my_properties')

    return render(request, 'core/delete_confirm.html', {'property': property_obj})


@login_required
def request_rental(request, pk):
    """Submit a rental request for a property (Tenant Only)."""
    # Role Check: Only Tenants (or superuser) can submit rental requests
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Property Owners cannot submit rental requests.")
        return redirect('core:public_property_detail', pk=pk)

    property_obj = get_object_or_404(Property, pk=pk, is_available=True)

    # Duplicate Pending Request Check
    existing_request = RentalRequest.objects.filter(
        tenant=request.user,
        property=property_obj,
        status=RentalRequest.STATUS_PENDING
    ).first()

    if existing_request:
        messages.info(request, f"You already have a Pending rental request for '{property_obj.title}'.")
        return redirect('core:my_rental_requests')

    if request.method == 'POST':
        form = RentalRequestForm(request.POST)
        if form.is_valid():
            req_obj = form.save(commit=False)
            req_obj.tenant = request.user
            req_obj.property = property_obj
            req_obj.owner = property_obj.owner
            req_obj.status = RentalRequest.STATUS_PENDING
            req_obj.save()

            messages.success(request, f"Rental request for '{property_obj.title}' submitted successfully!")
            return redirect('core:my_rental_requests')
        else:
            messages.error(request, "Please correct the errors in the rental request form.")
    else:
        form = RentalRequestForm()

    return render(request, 'core/request_rental.html', {
        'form': form,
        'property': property_obj
    })


@login_required
def my_rental_requests(request):
    """View rental requests submitted by the logged-in tenant (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Only Tenants can view submitted rental requests.")
        return redirect('accounts:owner_dashboard')

    tenant_requests = RentalRequest.objects.filter(tenant=request.user).order_by('-created_at')
    return render(request, 'core/my_rental_requests.html', {
        'rental_requests': tenant_requests
    })


@owner_required
def incoming_rental_requests(request):
    """View incoming rental requests for properties owned by the user (Owner Only)."""
    owner_requests = RentalRequest.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'core/incoming_rental_requests.html', {
        'incoming_requests': owner_requests
    })


@owner_required
def accept_rental_request(request, pk):
    """Accept a rental request and create an active tenancy (Owner Only)."""
    rental_request = get_object_or_404(RentalRequest, pk=pk)

    # Ownership check
    if rental_request.owner != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only process requests for your own properties.")
        return redirect('core:incoming_rental_requests')

    # Status check
    if rental_request.status != RentalRequest.STATUS_PENDING:
        messages.error(request, "This rental request has already been processed.")
        return redirect('core:incoming_rental_requests')

    # Availability / Active tenancy check
    if not rental_request.property.is_available or Tenancy.objects.filter(property=rental_request.property, status=Tenancy.STATUS_ACTIVE).exists():
        messages.error(request, "This property is no longer available or already has an active tenancy.")
        return redirect('core:incoming_rental_requests')

    if request.method == 'POST':
        form = TenancyAcceptForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Re-verify availability within transaction
                if Tenancy.objects.filter(property=rental_request.property, status=Tenancy.STATUS_ACTIVE).exists():
                    messages.error(request, "This property already has an active tenancy.")
                    return redirect('core:incoming_rental_requests')

                tenancy = form.save(commit=False)
                tenancy.tenant = rental_request.tenant
                tenancy.property = rental_request.property
                tenancy.owner = rental_request.owner
                tenancy.rental_request = rental_request
                tenancy.status = Tenancy.STATUS_ACTIVE
                tenancy.save()

                rental_request.status = RentalRequest.STATUS_ACCEPTED
                rental_request.save()

                prop = rental_request.property
                prop.is_available = False
                prop.save()

                # Automatically reject other pending requests for this property
                RentalRequest.objects.filter(
                    property=prop,
                    status=RentalRequest.STATUS_PENDING
                ).exclude(pk=rental_request.pk).update(status=RentalRequest.STATUS_REJECTED)

            tenant_name = rental_request.tenant.get_full_name() or rental_request.tenant.username
            messages.success(request, f"Rental request accepted! Active tenancy created for {tenant_name}.")
            return redirect('core:active_tenants')
        else:
            messages.error(request, "Please correct the errors in the tenancy setup form.")
    else:
        initial_data = {
            'rental_start_date': rental_request.requested_move_in_date,
            'monthly_rent': rental_request.property.monthly_rent,
            'security_deposit': rental_request.property.security_deposit,
            'rent_due_day': 5,
        }
        form = TenancyAcceptForm(initial=initial_data)

    return render(request, 'core/accept_rental_request.html', {
        'form': form,
        'rental_request': rental_request
    })


@owner_required
@require_POST
def reject_rental_request(request, pk):
    """Reject a rental request (Owner Only)."""
    rental_request = get_object_or_404(RentalRequest, pk=pk)

    # Ownership check
    if rental_request.owner != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only reject requests for your own properties.")
        return redirect('core:incoming_rental_requests')

    # Status check
    if rental_request.status != RentalRequest.STATUS_PENDING:
        messages.error(request, "This rental request has already been processed.")
        return redirect('core:incoming_rental_requests')

    rental_request.status = RentalRequest.STATUS_REJECTED
    rental_request.save()

    tenant_name = rental_request.tenant.get_full_name() or rental_request.tenant.username
    messages.info(request, f"Rental request from {tenant_name} has been rejected.")
    return redirect('core:incoming_rental_requests')


@owner_required
def active_tenants(request):
    """List active tenancies for properties owned by the logged-in owner (Owner Only)."""
    tenancies = Tenancy.objects.filter(
        owner=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('tenant', 'property').order_by('-created_at')

    return render(request, 'core/active_tenants.html', {
        'tenancies': tenancies
    })


@login_required
def tenant_rent_history(request):
    """View rent records history for the logged-in tenant (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Rent history is only accessible to Tenants.")
        return redirect('accounts:owner_dashboard')

    # Ensure current month rent record is created for active tenancies
    active_tenancies = Tenancy.objects.filter(tenant=request.user, status=Tenancy.STATUS_ACTIVE)
    for tenancy in active_tenancies:
        tenancy.get_or_create_current_rent_record()

    # Security: Restrict strictly to tenant's own tenancies
    rent_records = RentRecord.objects.filter(
        tenancy__tenant=request.user
    ).select_related('tenancy', 'tenancy__property').order_by('-rent_month')

    return render(request, 'core/tenant_rent_history.html', {
        'rent_records': rent_records
    })


@owner_required
def owner_rent_tracking(request):
    """View rent records tracking for tenancies belonging to owner's properties (Owner Only)."""
    # Ensure current month rent record is created for active tenancies owned by user
    owner_active_tenancies = Tenancy.objects.filter(owner=request.user, status=Tenancy.STATUS_ACTIVE)
    for tenancy in owner_active_tenancies:
        tenancy.get_or_create_current_rent_record()

    # Security: Restrict strictly to tenancies owned by the user
    rent_records = RentRecord.objects.filter(
        tenancy__owner=request.user
    ).select_related('tenancy', 'tenancy__tenant', 'tenancy__property', 'payment').order_by('-rent_month')

    return render(request, 'core/owner_rent_tracking.html', {
        'rent_records': rent_records
    })


@login_required
def pay_rent(request, pk):
    """Simulated payment view for a rent record (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Property Owners cannot make rent payments.")
        return redirect('accounts:owner_dashboard')

    rent_record = get_object_or_404(RentRecord, pk=pk)

    # Security check: Tenant can only pay for their own tenancy
    if rent_record.tenancy.tenant != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only pay rent for your own tenancy.")
        return redirect('core:tenant_rent_history')

    # Security check: Prevent paying already paid rent
    if rent_record.payment_status == RentRecord.STATUS_PAID or hasattr(rent_record, 'payment'):
        messages.info(request, "This rent record has already been paid.")
        return redirect('core:tenant_rent_history')

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', Payment.PAYMENT_METHOD_UPI)
        valid_methods = [choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES]
        if payment_method not in valid_methods:
            payment_method = Payment.PAYMENT_METHOD_UPI

        with transaction.atomic():
            # Double check payment status inside transaction
            if RentRecord.objects.filter(pk=pk, payment_status=RentRecord.STATUS_PAID).exists() or Payment.objects.filter(rent_record=rent_record).exists():
                messages.warning(request, "Payment has already been completed for this rent record.")
                return redirect('core:tenant_rent_history')

            txn_id = generate_transaction_id()
            payment = Payment.objects.create(
                rent_record=rent_record,
                tenant=request.user,
                owner=rent_record.tenancy.owner,
                property=rent_record.tenancy.property,
                amount_paid=rent_record.amount,
                payment_method=payment_method,
                transaction_id=txn_id
            )

            rent_record.payment_status = RentRecord.STATUS_PAID
            rent_record.paid_date = payment.paid_at
            rent_record.save()

        messages.success(request, f"Simulated rent payment of ₹{payment.amount_paid} completed successfully!")
        return redirect('core:payment_success', pk=payment.pk)

    return render(request, 'core/pay_rent.html', {
        'rent_record': rent_record,
        'payment_methods': Payment.PAYMENT_METHOD_CHOICES
    })


@login_required
def payment_success(request, pk):
    """Payment success confirmation page (Tenant Only)."""
    payment = get_object_or_404(Payment, pk=pk)

    # Security check: Tenant can only view their own payment success page
    if payment.tenant != request.user and not request.user.is_superuser:
        messages.error(request, "Access denied. You can only view your own payment receipts.")
        return redirect('core:tenant_payment_history')

    return render(request, 'core/payment_success.html', {
        'payment': payment
    })


@login_required
def tenant_payment_history(request):
    """View payment history statement for the logged-in tenant (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Payment history is restricted to Tenants.")
        return redirect('accounts:owner_dashboard')

    payments = Payment.objects.filter(
        tenant=request.user
    ).select_related('rent_record', 'property', 'owner').order_by('-paid_at')

    return render(request, 'core/tenant_payment_history.html', {
        'payments': payments
    })


@login_required
def view_receipt(request, pk):
    """View printable rent payment receipt for a completed payment."""
    payment = get_object_or_404(
        Payment.objects.select_related('rent_record', 'tenant', 'owner', 'property'),
        pk=pk
    )

    # Security Check: Only assigned tenant, property owner, or superuser can view receipt
    if request.user != payment.tenant and request.user != payment.owner and not request.user.is_superuser:
        return HttpResponseForbidden("Access denied. You do not have permission to view this receipt.")

    return render(request, 'core/view_receipt.html', {
        'payment': payment
    })


# Utility Bill Management Views (Phase 6)

@owner_required
def owner_utility_bills(request):
    """View monthly utility bills for properties owned by the user (Owner Only)."""
    utility_bills = UtilityBill.objects.filter(
        tenancy__owner=request.user
    ).select_related('tenancy', 'tenancy__tenant', 'tenancy__property').order_by('-billing_month', '-created_at')

    return render(request, 'core/owner_utility_bills.html', {
        'utility_bills': utility_bills
    })


@owner_required
def add_utility_bill(request):
    """Create a new monthly utility bill for an active tenancy (Owner Only)."""
    import datetime
    active_tenancies = Tenancy.objects.filter(
        owner=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('property', 'tenant')

    if not active_tenancies.exists():
        messages.warning(request, "You do not have any active tenancies to create utility bills for.")
        return redirect('core:owner_utility_bills')

    selected_tenancy_id = request.GET.get('tenancy') or request.POST.get('tenancy')
    initial_data = {}
    if selected_tenancy_id:
        initial_data['tenancy'] = selected_tenancy_id

    # Default billing month to current month YYYY-MM
    initial_data['billing_month'] = datetime.date.today().strftime('%Y-%m')

    if request.method == 'POST':
        form = UtilityBillForm(owner=request.user, data=request.POST)
        if form.is_valid():
            tenancy = form.cleaned_data['tenancy']
            # Security check: Ensure selected tenancy belongs to logged in owner
            if tenancy.owner != request.user and not request.user.is_superuser:
                return HttpResponseForbidden("Access denied. You can only create utility bills for your own properties.")

            utility_bill = form.save()
            messages.success(
                request,
                f"Utility bill of ₹{utility_bill.total_utility_charges:,.2f} for {utility_bill.billing_month.strftime('%B %Y')} added successfully for {tenancy.property.title}."
            )
            return redirect('core:owner_utility_bills')
        else:
            messages.error(request, "Please correct the errors in the utility bill form below.")
    else:
        form = UtilityBillForm(owner=request.user, initial=initial_data)

    return render(request, 'core/add_utility_bill.html', {
        'form': form,
        'active_tenancies': active_tenancies
    })


@login_required
def tenant_utility_bills(request):
    """View utility bills for the logged-in tenant's active tenancy (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Tenant utility bills page is restricted to Tenants.")
        return redirect('accounts:owner_dashboard')

    active_tenancy = Tenancy.objects.filter(
        tenant=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('property', 'owner').first()

    utility_bills = UtilityBill.objects.filter(
        tenancy__tenant=request.user
    ).select_related('tenancy', 'tenancy__property', 'tenancy__owner').order_by('-billing_month', '-created_at')

    return render(request, 'core/tenant_utility_bills.html', {
        'active_tenancy': active_tenancy,
        'utility_bills': utility_bills
    })


# Maintenance Request Views (Phase 7)

@login_required
def report_maintenance(request):
    """Submit a new maintenance request (Tenant Only, Active Tenancy Required)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Only Tenants can submit maintenance requests.")
        return redirect('accounts:owner_dashboard')

    active_tenancy = Tenancy.objects.filter(
        tenant=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('property', 'owner').first()

    if not active_tenancy:
        messages.warning(request, "You must have an active tenancy to submit a maintenance request.")
        return redirect('accounts:tenant_dashboard')

    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            mreq = form.save(commit=False)
            mreq.tenancy = active_tenancy
            mreq.tenant = request.user
            mreq.save()
            messages.success(request, f"Maintenance request '{mreq.title}' submitted successfully.")
            return redirect('core:tenant_maintenance_list')
        else:
            messages.error(request, "Please correct the errors in the maintenance request form below.")
    else:
        form = MaintenanceRequestForm()

    return render(request, 'core/report_maintenance.html', {
        'form': form,
        'active_tenancy': active_tenancy
    })


@login_required
def tenant_maintenance_list(request):
    """View maintenance request history for logged-in tenant (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Maintenance history is restricted to Tenants.")
        return redirect('accounts:owner_dashboard')

    maintenance_requests = MaintenanceRequest.objects.filter(
        tenant=request.user
    ).select_related('tenancy', 'tenancy__property').order_by('-submitted_at')

    return render(request, 'core/tenant_maintenance_list.html', {
        'maintenance_requests': maintenance_requests
    })


@login_required
def tenant_maintenance_detail(request, pk):
    """View detailed maintenance request & owner response for tenant (Tenant Only)."""
    mreq = get_object_or_404(
        MaintenanceRequest.objects.select_related('tenancy', 'tenancy__property', 'tenancy__owner'),
        pk=pk
    )

    if mreq.tenant != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("Access denied. You can only view your own maintenance requests.")

    return render(request, 'core/tenant_maintenance_detail.html', {
        'mreq': mreq
    })


@owner_required
def owner_maintenance_list(request):
    """View incoming maintenance requests for properties owned by the user (Owner Only)."""
    maintenance_requests = MaintenanceRequest.objects.filter(
        tenancy__owner=request.user
    ).select_related('tenancy', 'tenancy__property', 'tenant').order_by('-submitted_at')

    return render(request, 'core/owner_maintenance_list.html', {
        'maintenance_requests': maintenance_requests
    })


@owner_required
def owner_maintenance_detail(request, pk):
    """View and update maintenance request status and response note (Owner Only)."""
    from django.utils import timezone

    mreq = get_object_or_404(
        MaintenanceRequest.objects.select_related('tenancy', 'tenancy__property', 'tenant'),
        pk=pk
    )

    if mreq.tenancy.owner != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("Access denied. You can only manage maintenance requests for your own properties.")

    if request.method == 'POST':
        form = MaintenanceUpdateForm(request.POST, instance=mreq)
        if form.is_valid():
            updated_mreq = form.save(commit=False)
            if updated_mreq.status == MaintenanceRequest.STATUS_COMPLETED:
                if not updated_mreq.completed_at:
                    updated_mreq.completed_at = timezone.now()
            else:
                updated_mreq.completed_at = None

            updated_mreq.save()
            messages.success(request, f"Maintenance request #{mreq.pk} status updated to '{mreq.get_status_display()}'.")
            return redirect('core:owner_maintenance_list')
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        form = MaintenanceUpdateForm(instance=mreq)

    return render(request, 'core/owner_maintenance_detail.html', {
        'mreq': mreq,
        'form': form
    })


# Rental Agreement & Renewal Views (Phase 8)

@login_required
def tenant_agreement(request):
    """View rental agreement details & renewal history for logged-in tenant (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Agreement details page is restricted to Tenants.")
        return redirect('accounts:owner_dashboard')

    active_tenancy = Tenancy.objects.filter(
        tenant=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('property', 'owner').first()

    renewal_requests = []
    pending_renewal = None
    if active_tenancy:
        renewal_requests = RenewalRequest.objects.filter(
            tenancy=active_tenancy
        ).order_by('-created_at')
        pending_renewal = renewal_requests.filter(status=RenewalRequest.STATUS_PENDING).first()

    return render(request, 'core/tenant_agreement.html', {
        'active_tenancy': active_tenancy,
        'renewal_requests': renewal_requests,
        'pending_renewal': pending_renewal
    })


@login_required
def request_agreement_renewal(request):
    """Submit a lease renewal request for tenant's active tenancy (Tenant Only)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Renewal requests are restricted to Tenants.")
        return redirect('accounts:owner_dashboard')

    active_tenancy = Tenancy.objects.filter(
        tenant=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('property', 'owner').first()

    if not active_tenancy:
        messages.warning(request, "You must have an active tenancy to submit a lease renewal request.")
        return redirect('accounts:tenant_dashboard')

    # Security check: Prevent duplicate pending requests for same tenancy
    if RenewalRequest.objects.filter(tenancy=active_tenancy, status=RenewalRequest.STATUS_PENDING).exists():
        messages.warning(request, "You already have a pending lease renewal request for this tenancy.")
        return redirect('core:tenant_agreement')

    if request.method == 'POST':
        form = RenewalRequestForm(tenancy=active_tenancy, data=request.POST)
        if form.is_valid():
            renewal = form.save(commit=False)
            renewal.tenancy = active_tenancy
            renewal.tenant = request.user
            renewal.save()
            messages.success(
                request,
                f"Renewal request for new end date {renewal.requested_new_end_date.strftime('%b %d, %Y')} submitted successfully."
            )
            return redirect('core:tenant_agreement')
        else:
            messages.error(request, "Please correct the errors in the renewal request form below.")
    else:
        form = RenewalRequestForm(tenancy=active_tenancy)

    return render(request, 'core/request_agreement_renewal.html', {
        'form': form,
        'active_tenancy': active_tenancy
    })


@owner_required
def owner_renewal_requests(request):
    """View lease renewal requests for properties owned by the user (Owner Only)."""
    renewal_requests = RenewalRequest.objects.filter(
        tenancy__owner=request.user
    ).select_related('tenancy', 'tenancy__property', 'tenant').order_by('-created_at')

    return render(request, 'core/owner_renewal_requests.html', {
        'renewal_requests': renewal_requests
    })


@owner_required
def approve_renewal_request(request, pk):
    """Approve a lease renewal request and update tenancy end date (Owner Only)."""
    renewal = get_object_or_404(
        RenewalRequest.objects.select_related('tenancy', 'tenancy__owner'),
        pk=pk
    )

    if renewal.tenancy.owner != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("Access denied. You can only manage renewal requests for your own properties.")

    if renewal.status != RenewalRequest.STATUS_PENDING:
        messages.info(request, f"This renewal request has already been {renewal.get_status_display().lower()}.")
        return redirect('core:owner_renewal_requests')

    if request.method == 'POST':
        owner_response = request.POST.get('owner_response', '').strip()
        with transaction.atomic():
            renewal.status = RenewalRequest.STATUS_APPROVED
            renewal.owner_response = owner_response
            renewal.save()

            # Atomic update of tenancy end date
            tenancy = renewal.tenancy
            tenancy.rental_end_date = renewal.requested_new_end_date
            tenancy.save()

        messages.success(
            request,
            f"Renewal request approved! Tenancy end date updated to {renewal.requested_new_end_date.strftime('%b %d, %Y')}."
        )
        return redirect('core:owner_renewal_requests')

    return redirect('core:owner_renewal_requests')


@owner_required
def reject_renewal_request(request, pk):
    """Reject a lease renewal request without altering tenancy end date (Owner Only)."""
    renewal = get_object_or_404(
        RenewalRequest.objects.select_related('tenancy', 'tenancy__owner'),
        pk=pk
    )

    if renewal.tenancy.owner != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("Access denied. You can only manage renewal requests for your own properties.")

    if renewal.status != RenewalRequest.STATUS_PENDING:
        messages.info(request, f"This renewal request has already been {renewal.get_status_display().lower()}.")
        return redirect('core:owner_renewal_requests')

    if request.method == 'POST':
        owner_response = request.POST.get('owner_response', '').strip()
        renewal.status = RenewalRequest.STATUS_REJECTED
        renewal.owner_response = owner_response
        renewal.save()

        messages.info(request, f"Renewal request for {renewal.tenancy.property.title} was rejected.")
        return redirect('core:owner_renewal_requests')

    return redirect('core:owner_renewal_requests')











