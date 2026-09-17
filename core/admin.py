from django.contrib import admin
from .models import Property, PropertyImage, RentalRequest, Tenancy, RentRecord, Payment, UtilityBill, MaintenanceRequest, RenewalRequest

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'location', 'monthly_rent', 'property_type', 'is_available', 'created_at')
    list_filter = ('property_type', 'furnished_status', 'is_available', 'wifi_available', 'parking_available')
    search_fields = ('title', 'location', 'address', 'owner__username', 'owner__email')
    inlines = [PropertyImageInline]

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'image', 'uploaded_at')

@admin.register(RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'property', 'owner', 'requested_move_in_date', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tenant__username', 'tenant__email', 'property__title', 'owner__username')

@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
    list_display = ('property', 'tenant', 'owner', 'rental_start_date', 'rental_end_date', 'monthly_rent', 'rent_due_day', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('property__title', 'tenant__username', 'owner__username')

@admin.register(RentRecord)
class RentRecordAdmin(admin.ModelAdmin):
    list_display = ('tenancy', 'rent_month', 'amount', 'due_date', 'payment_status', 'paid_date')
    list_filter = ('payment_status', 'rent_month')
    search_fields = ('tenancy__property__title', 'tenancy__tenant__username', 'tenancy__owner__username')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'tenant', 'property', 'amount_paid', 'payment_method', 'paid_at')
    list_filter = ('payment_method', 'paid_at')
    search_fields = ('transaction_id', 'tenant__username', 'property__title', 'owner__username')

@admin.register(UtilityBill)
class UtilityBillAdmin(admin.ModelAdmin):
    list_display = ('tenancy', 'billing_month', 'electricity_charge', 'water_charge', 'maintenance_charge', 'other_charge', 'total_utility_charges', 'created_at')
    list_filter = ('billing_month', 'created_at')
    search_fields = ('tenancy__property__title', 'tenancy__tenant__username', 'tenancy__owner__username')

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenancy', 'tenant', 'category', 'priority', 'status', 'submitted_at', 'completed_at')
    list_filter = ('category', 'priority', 'status', 'submitted_at')
    search_fields = ('title', 'description', 'tenant__username', 'tenancy__property__title')

@admin.register(RenewalRequest)
class RenewalRequestAdmin(admin.ModelAdmin):
    list_display = ('tenancy', 'tenant', 'requested_new_end_date', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tenancy__property__title', 'tenant__username', 'tenancy__owner__username')








