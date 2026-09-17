from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    # Public Property Routes (Phase 3B)
    path('properties/', views.properties, name='properties'),
    path('properties/<int:pk>/', views.public_property_detail, name='public_property_detail'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('about/', views.about, name='about'),
    
    # Owner Property Management Routes (Phase 3A)
    path('property/add/', views.add_property, name='add_property'),
    path('my-properties/', views.my_properties, name='my_properties'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('property/<int:pk>/edit/', views.edit_property, name='edit_property'),
    path('property/<int:pk>/delete/', views.delete_property, name='delete_property'),

    # Tenant & Owner Rental Request Routes (Phase 4A & 4B)
    path('properties/<int:pk>/request/', views.request_rental, name='request_rental'),
    path('tenant/requests/', views.my_rental_requests, name='my_rental_requests'),
    path('owner/incoming-requests/', views.incoming_rental_requests, name='incoming_rental_requests'),
    path('owner/requests/<int:pk>/accept/', views.accept_rental_request, name='accept_rental_request'),
    path('owner/requests/<int:pk>/reject/', views.reject_rental_request, name='reject_rental_request'),
    path('owner/active-tenants/', views.active_tenants, name='active_tenants'),

    # Rent Tracking & History Routes (Phase 5A & 5B)
    path('tenant/rent-history/', views.tenant_rent_history, name='tenant_rent_history'),
    path('owner/rent-tracking/', views.owner_rent_tracking, name='owner_rent_tracking'),

    # Simulated Rent Payment & Receipt Routes (Phase 5B & 5C)
    path('tenant/rent-records/<int:pk>/pay/', views.pay_rent, name='pay_rent'),
    path('tenant/payments/<int:pk>/success/', views.payment_success, name='payment_success'),
    path('tenant/payment-history/', views.tenant_payment_history, name='tenant_payment_history'),
    path('tenant/payments/<int:pk>/receipt/', views.view_receipt, name='view_receipt'),

    # Utility Bill Management Routes (Phase 6)
    path('owner/utility-bills/', views.owner_utility_bills, name='owner_utility_bills'),
    path('owner/utility-bills/add/', views.add_utility_bill, name='add_utility_bill'),
    path('tenant/utility-bills/', views.tenant_utility_bills, name='tenant_utility_bills'),

    # Maintenance Request Routes (Phase 7)
    path('tenant/maintenance/report/', views.report_maintenance, name='report_maintenance'),
    path('tenant/maintenance/', views.tenant_maintenance_list, name='tenant_maintenance_list'),
    path('tenant/maintenance/<int:pk>/', views.tenant_maintenance_detail, name='tenant_maintenance_detail'),
    path('owner/maintenance/', views.owner_maintenance_list, name='owner_maintenance_list'),
    path('owner/maintenance/<int:pk>/', views.owner_maintenance_detail, name='owner_maintenance_detail'),

    # Rental Agreement & Renewal Routes (Phase 8)
    path('tenant/agreement/', views.tenant_agreement, name='tenant_agreement'),
    path('tenant/agreement/renew/', views.request_agreement_renewal, name='request_agreement_renewal'),
    path('owner/renewal-requests/', views.owner_renewal_requests, name='owner_renewal_requests'),
    path('owner/renewal-requests/<int:pk>/approve/', views.approve_renewal_request, name='approve_renewal_request'),
    path('owner/renewal-requests/<int:pk>/reject/', views.reject_renewal_request, name='reject_renewal_request'),
]









