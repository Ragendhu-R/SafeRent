from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import SignUpForm, LoginForm, ProfileUpdateForm

User = get_user_model()

def signup_view(request):
    """User Registration View for Tenant and Property Owner roles."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to SafeRent, {user.first_name}! Account created successfully.")
            return _redirect_by_role(user)
        else:
            messages.error(request, "Please correct the errors below to complete registration.")
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    """User Login View."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return _redirect_by_role(user)
            else:
                messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User Logout View."""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('core:home')


@login_required
def profile_view(request):
    """User Profile View & Edit."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors in the profile form.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'user_obj': request.user
    })


@login_required
def tenant_dashboard(request):
    """Tenant Dashboard View (Role Restricted)."""
    if request.user.role != User.ROLE_TENANT and not request.user.is_superuser:
        messages.warning(request, "Access denied. Only Tenants can access the Tenant Dashboard.")
        return redirect('accounts:owner_dashboard')

    from core.models import Tenancy, UtilityBill, MaintenanceRequest
    active_tenancy = Tenancy.objects.filter(
        tenant=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).select_related('property', 'owner').first()

    current_rent_record = None
    latest_utility_bill = None
    combined_monthly_amount = None

    if active_tenancy:
        current_rent_record = active_tenancy.get_or_create_current_rent_record()
        latest_utility_bill = UtilityBill.objects.filter(
            tenancy=active_tenancy
        ).order_by('-billing_month', '-created_at').first()

        if latest_utility_bill:
            combined_monthly_amount = active_tenancy.monthly_rent + latest_utility_bill.total_utility_charges

    open_maintenance_count = MaintenanceRequest.objects.filter(
        tenant=request.user,
        status__in=[MaintenanceRequest.STATUS_PENDING, MaintenanceRequest.STATUS_ACCEPTED, MaintenanceRequest.STATUS_IN_PROGRESS]
    ).count()

    return render(request, 'accounts/tenant_dashboard.html', {
        'active_tenancy': active_tenancy,
        'current_rent_record': current_rent_record,
        'latest_utility_bill': latest_utility_bill,
        'combined_monthly_amount': combined_monthly_amount,
        'open_maintenance_count': open_maintenance_count,
    })



@login_required
def owner_dashboard(request):
    """Property Owner Dashboard View (Role Restricted)."""
    if request.user.role != User.ROLE_OWNER and not request.user.is_superuser:
        messages.warning(request, "Access denied. Only Property Owners can access the Owner Dashboard.")
        return redirect('accounts:tenant_dashboard')

    from core.models import Tenancy, UtilityBill, MaintenanceRequest, RenewalRequest
    active_tenants_count = Tenancy.objects.filter(
        owner=request.user,
        status=Tenancy.STATUS_ACTIVE
    ).count()

    utility_bills_count = UtilityBill.objects.filter(
        tenancy__owner=request.user
    ).count()

    open_maintenance_count = MaintenanceRequest.objects.filter(
        tenancy__owner=request.user,
        status__in=[MaintenanceRequest.STATUS_PENDING, MaintenanceRequest.STATUS_ACCEPTED, MaintenanceRequest.STATUS_IN_PROGRESS]
    ).count()

    pending_renewal_count = RenewalRequest.objects.filter(
        tenancy__owner=request.user,
        status=RenewalRequest.STATUS_PENDING
    ).count()

    return render(request, 'accounts/owner_dashboard.html', {
        'active_tenants_count': active_tenants_count,
        'utility_bills_count': utility_bills_count,
        'open_maintenance_count': open_maintenance_count,
        'pending_renewal_count': pending_renewal_count,
    })






def _redirect_by_role(user):
    """Helper function to redirect authenticated user to their role-specific dashboard."""
    if user.is_superuser or user.role == User.ROLE_OWNER:
        return redirect('accounts:owner_dashboard')
    return redirect('accounts:tenant_dashboard')
