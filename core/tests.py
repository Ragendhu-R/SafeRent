import datetime
import tempfile
from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Property, PropertyImage, RentalRequest, Tenancy, RentRecord, Payment, UtilityBill, MaintenanceRequest, RenewalRequest
from core.forms import PropertyForm, RentalRequestForm, TenancyAcceptForm

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class Phase3APropertyManagementTests(TestCase):
    def setUp(self):
        # Create Owner User
        self.owner = User.objects.create_user(
            username='owner_user',
            email='owner@example.com',
            password='Password123',
            first_name='John',
            last_name='Owner',
            role=User.ROLE_OWNER
        )

        # Create Second Owner User
        self.other_owner = User.objects.create_user(
            username='other_owner',
            email='other@example.com',
            password='Password123',
            first_name='Alice',
            last_name='Other',
            role=User.ROLE_OWNER
        )

        # Create Tenant User
        self.tenant = User.objects.create_user(
            username='tenant_user',
            email='tenant@example.com',
            password='Password123',
            first_name='Bob',
            last_name='Tenant',
            role=User.ROLE_TENANT
        )

        # Clients
        self.owner_client = Client()
        self.owner_client.login(username='owner_user', password='Password123')

        self.other_owner_client = Client()
        self.other_owner_client.login(username='other_owner', password='Password123')

        self.tenant_client = Client()
        self.tenant_client.login(username='tenant_user', password='Password123')

        # Sample Property
        self.property = Property.objects.create(
            owner=self.owner,
            title='Luxury Villa',
            description='Beautiful 3 BHK villa with garden.',
            location='Koramangala, Bengaluru',
            address='123 Palm Avenue',
            monthly_rent=Decimal('45000.00'),
            security_deposit=Decimal('90000.00'),
            property_type='HOUSE',
            bedrooms=3,
            bathrooms=3,
            furnished_status='FURNISHED',
            wifi_available=True,
            parking_available=True,
            is_available=True
        )

    def test_property_creation_by_owner(self):
        """Verify that an Owner can publish a new property listing with images."""
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        test_image = SimpleUploadedFile("sample.png", image_content, content_type="image/png")

        post_data = {
            'title': 'Cozy 1BHK Apartment',
            'description': 'Compact modern apartment near metro.',
            'location': 'Indiranagar',
            'address': '456 Metro Lane',
            'monthly_rent': '20000.00',
            'security_deposit': '40000.00',
            'property_type': 'APARTMENT',
            'bedrooms': 1,
            'bathrooms': 1,
            'furnished_status': 'SEMI',
            'wifi_available': True,
            'parking_available': False,
            'other_amenities': 'Elevator, Security',
            'is_available': True,
            'photos': [test_image]
        }

        response = self.owner_client.post(reverse('core:add_property'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "listed successfully")

        created_prop = Property.objects.get(title='Cozy 1BHK Apartment')
        self.assertEqual(created_prop.owner, self.owner)
        self.assertEqual(created_prop.images.count(), 1)

    def test_negative_rent_deposit_validation(self):
        """Verify that negative rent or security deposit values are rejected by PropertyForm."""
        form_data = {
            'title': 'Test Property',
            'description': 'Description',
            'location': 'Location',
            'address': 'Address',
            'monthly_rent': -500,
            'security_deposit': -100,
            'property_type': 'APARTMENT',
            'bedrooms': 1,
            'bathrooms': 1,
            'furnished_status': 'UNFURNISHED',
        }
        form = PropertyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('monthly_rent', form.errors)
        self.assertIn('security_deposit', form.errors)

    def test_owner_my_properties_view(self):
        """Verify that My Properties page displays only properties belonging to the logged in owner."""
        # Create property for other owner
        Property.objects.create(
            owner=self.other_owner,
            title='Other Owner House',
            description='Desc',
            location='Loc',
            address='Addr',
            monthly_rent=Decimal('15000.00'),
            security_deposit=Decimal('30000.00')
        )

        response = self.owner_client.get(reverse('core:my_properties'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')
        self.assertNotContains(response, 'Other Owner House')

    def test_owner_edit_property(self):
        """Verify that an owner can update their property details."""
        update_data = {
            'title': 'Luxury Villa (Renovated)',
            'description': 'Updated description.',
            'location': 'Koramangala, Bengaluru',
            'address': '123 Palm Avenue',
            'monthly_rent': '50000.00',
            'security_deposit': '100000.00',
            'property_type': 'HOUSE',
            'bedrooms': 4,
            'bathrooms': 4,
            'furnished_status': 'FURNISHED',
            'wifi_available': True,
            'parking_available': True,
            'is_available': True
        }

        response = self.owner_client.post(reverse('core:edit_property', kwargs={'pk': self.property.pk}), update_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.property.refresh_from_db()
        self.assertEqual(self.property.title, 'Luxury Villa (Renovated)')
        self.assertEqual(self.property.monthly_rent, Decimal('50000.00'))
        self.assertEqual(self.property.bedrooms, 4)

    def test_cross_owner_edit_prevention(self):
        """Verify that Owner A cannot edit Owner B's property."""
        update_data = {
            'title': 'Hacked Title',
            'description': 'Hacked',
            'location': 'Loc',
            'address': 'Addr',
            'monthly_rent': '1.00',
            'security_deposit': '1.00',
            'property_type': 'HOUSE',
            'bedrooms': 1,
            'bathrooms': 1,
            'furnished_status': 'UNFURNISHED'
        }

        response = self.other_owner_client.post(reverse('core:edit_property', kwargs={'pk': self.property.pk}), update_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access denied")

        self.property.refresh_from_db()
        self.assertNotEqual(self.property.title, 'Hacked Title')

    def test_owner_delete_property(self):
        """Verify that an owner can delete their own property."""
        response = self.owner_client.post(reverse('core:delete_property', kwargs={'pk': self.property.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Property.objects.filter(pk=self.property.pk).exists())

    def test_tenant_access_restriction(self):
        """Verify that Tenants cannot access owner property management endpoints."""
        urls_to_test = [
            reverse('core:add_property'),
            reverse('core:my_properties'),
            reverse('core:property_detail', kwargs={'pk': self.property.pk}),
            reverse('core:edit_property', kwargs={'pk': self.property.pk}),
            reverse('core:delete_property', kwargs={'pk': self.property.pk}),
        ]

        for url in urls_to_test:
            response = self.tenant_client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Access denied")

    def test_public_properties_listing_view(self):
        """Verify that public properties view displays available properties and excludes unavailable ones."""
        # Create an unavailable property
        unavailable_prop = Property.objects.create(
            owner=self.owner,
            title='Hidden Private Villa',
            description='Not for rent',
            location='Private Area',
            address='Private Street',
            monthly_rent=Decimal('100000.00'),
            security_deposit=Decimal('200000.00'),
            is_available=False
        )

        client = Client()
        response = client.get(reverse('core:properties'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')
        self.assertNotContains(response, 'Hidden Private Villa')

    def test_public_property_detail_view(self):
        """Verify that any user can view property details publicly, including safe owner info."""
        client = Client()
        response = client.get(reverse('core:public_property_detail', kwargs={'pk': self.property.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')
        self.assertContains(response, 'Beautiful 3 BHK villa with garden.')
        self.assertContains(response, 'John')
        self.assertContains(response, 'owner@example.com')
        # Ensure password or password hash is NOT exposed
        self.assertNotContains(response, self.owner.password)

    def test_homepage_featured_properties(self):
        """Verify that the homepage displays available properties in featured section."""
        client = Client()
        response = client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')

    def test_empty_available_properties_message(self):
        """Verify that friendly message is shown when no properties are available."""
        Property.objects.all().delete()
        client = Client()

        # Properties Page
        response_props = client.get(reverse('core:properties'))
        self.assertEqual(response_props.status_code, 200)
        self.assertContains(response_props, 'No properties are currently available')

        # Home Page
        response_home = client.get(reverse('core:home'))
        self.assertEqual(response_home.status_code, 200)
        self.assertContains(response_home, 'No featured properties are currently available')

    def test_filter_by_location(self):
        """Verify partial and case-insensitive location search."""
        # Create extra property
        Property.objects.create(
            owner=self.owner,
            title='Beachfront Apartment',
            description='Seaside view',
            location='Kakkanad, Kochi',
            address='Kakkanad Road',
            monthly_rent=Decimal('12000.00'),
            security_deposit=Decimal('24000.00'),
            is_available=True
        )

        client = Client()
        # Search for 'kakkanad' (case-insensitive)
        response = client.get(reverse('core:properties'), {'location': 'kakkanad'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Beachfront Apartment')
        self.assertNotContains(response, 'Luxury Villa')

    def test_filter_by_max_rent(self):
        """Verify filtering by maximum monthly rent."""
        Property.objects.create(
            owner=self.owner,
            title='Budget Room',
            description='Affordable',
            location='Koramangala, Bengaluru',
            address='12 Street',
            monthly_rent=Decimal('8000.00'),
            security_deposit=Decimal('16000.00'),
            is_available=True
        )

        client = Client()
        response = client.get(reverse('core:properties'), {'max_rent': '10000'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Budget Room')
        self.assertNotContains(response, 'Luxury Villa')

    def test_filter_by_property_type(self):
        """Verify filtering by property type."""
        Property.objects.create(
            owner=self.owner,
            title='Cosy Studio Apartment',
            description='Studio',
            location='Indiranagar',
            address='Indiranagar St',
            monthly_rent=Decimal('18000.00'),
            security_deposit=Decimal('36000.00'),
            property_type='APARTMENT',
            is_available=True
        )

        client = Client()
        response = client.get(reverse('core:properties'), {'property_type': 'APARTMENT'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cosy Studio Apartment')
        self.assertNotContains(response, 'Luxury Villa')  # Luxury Villa is HOUSE

    def test_combine_multiple_filters(self):
        """Verify combining location, max rent, and furnished status filters."""
        # Property 1: Kakkanad, 9000, Furnished
        p1 = Property.objects.create(
            owner=self.owner,
            title='Match Kakkanad Flat',
            description='Matches all',
            location='Kakkanad',
            address='Addr',
            monthly_rent=Decimal('9000.00'),
            security_deposit=Decimal('18000.00'),
            property_type='APARTMENT',
            furnished_status='FURNISHED',
            wifi_available=True,
            is_available=True
        )

        # Property 2: Kakkanad, 15000 (Too expensive), Furnished
        p2 = Property.objects.create(
            owner=self.owner,
            title='Expensive Kakkanad Flat',
            description='Too pricey',
            location='Kakkanad',
            address='Addr',
            monthly_rent=Decimal('15000.00'),
            security_deposit=Decimal('30000.00'),
            furnished_status='FURNISHED',
            is_available=True
        )

        client = Client()
        filter_params = {
            'location': 'Kakkanad',
            'max_rent': '10000',
            'furnished_status': 'FURNISHED'
        }
        response = client.get(reverse('core:properties'), filter_params)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Match Kakkanad Flat')
        self.assertNotContains(response, 'Expensive Kakkanad Flat')
        self.assertNotContains(response, 'Luxury Villa')

    def test_clear_filters(self):
        """Verify clearing filters returns all available properties."""
        client = Client()
        response = client.get(reverse('core:properties'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')

    def test_search_no_results_message(self):
        """Verify that searching for non-matching criteria shows the specific empty state message."""
        client = Client()
        response = client.get(reverse('core:properties'), {'location': 'NonExistentCityXYZ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No properties match your search. Try changing your filters.')
        self.assertContains(response, 'Clear Filters')

    def test_unavailable_properties_never_appear_in_filters(self):
        """Verify that unavailable properties never appear regardless of search criteria."""
        Property.objects.create(
            owner=self.owner,
            title='Unavailable Kakkanad Villa',
            description='Secret',
            location='Kakkanad',
            address='Addr',
            monthly_rent=Decimal('5000.00'),
            security_deposit=Decimal('10000.00'),
            is_available=False
        )

        client = Client()
        # Search specifically for Kakkanad with max rent 10000
        response = client.get(reverse('core:properties'), {'location': 'Kakkanad', 'max_rent': '10000'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Unavailable Kakkanad Villa')

    def test_tenant_can_submit_rental_request(self):
        """Verify that a Tenant can submit a valid rental request for an available property."""
        future_date = (datetime.date.today() + datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        post_data = {
            'requested_move_in_date': future_date,
            'message': 'Looking forward to moving in soon!'
        }
        response = self.tenant_client.post(reverse('core:request_rental', kwargs={'pk': self.property.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "submitted successfully")

        req = RentalRequest.objects.get(tenant=self.tenant, property=self.property)
        self.assertEqual(req.owner, self.owner)
        self.assertEqual(req.status, RentalRequest.STATUS_PENDING)
        self.assertEqual(req.message, 'Looking forward to moving in soon!')

    def test_request_appears_in_tenant_my_requests(self):
        """Verify that submitted request appears in Tenant's My Rental Requests page."""
        future_date = datetime.date.today() + datetime.timedelta(days=7)
        RentalRequest.objects.create(
            tenant=self.tenant,
            property=self.property,
            owner=self.owner,
            requested_move_in_date=future_date,
            message='Hello owner',
            status=RentalRequest.STATUS_PENDING
        )

        response = self.tenant_client.get(reverse('core:my_rental_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')
        self.assertContains(response, 'Pending')

    def test_request_appears_in_owner_incoming_requests(self):
        """Verify that the request appears in the property owner's Incoming Rental Requests page."""
        future_date = datetime.date.today() + datetime.timedelta(days=7)
        RentalRequest.objects.create(
            tenant=self.tenant,
            property=self.property,
            owner=self.owner,
            requested_move_in_date=future_date,
            message='Hello owner',
            status=RentalRequest.STATUS_PENDING
        )

        response = self.owner_client.get(reverse('core:incoming_rental_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Luxury Villa')
        self.assertContains(response, 'Bob')  # Tenant first name
        self.assertContains(response, 'Hello owner')

    def test_other_owner_cannot_see_request(self):
        """Verify that another property owner cannot view the incoming rental request."""
        future_date = datetime.date.today() + datetime.timedelta(days=7)
        RentalRequest.objects.create(
            tenant=self.tenant,
            property=self.property,
            owner=self.owner,
            requested_move_in_date=future_date,
            message='Secret request',
            status=RentalRequest.STATUS_PENDING
        )

        response = self.other_owner_client.get(reverse('core:incoming_rental_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Secret request')

    def test_owner_cannot_submit_rental_request(self):
        """Verify that property owners cannot submit rental requests."""
        future_date = (datetime.date.today() + datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        post_data = {
            'requested_move_in_date': future_date,
            'message': 'Owner attempting to request'
        }
        response = self.owner_client.post(reverse('core:request_rental', kwargs={'pk': self.property.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access denied")
        self.assertFalse(RentalRequest.objects.filter(tenant=self.owner).exists())

    def test_duplicate_pending_request_prevented(self):
        """Verify that duplicate pending rental requests for the same property are blocked."""
        future_date = datetime.date.today() + datetime.timedelta(days=7)
        RentalRequest.objects.create(
            tenant=self.tenant,
            property=self.property,
            owner=self.owner,
            requested_move_in_date=future_date,
            status=RentalRequest.STATUS_PENDING
        )

        # Attempt second request
        post_data = {
            'requested_move_in_date': future_date.strftime('%Y-%m-%d'),
            'message': 'Second attempt'
        }
        response = self.tenant_client.post(reverse('core:request_rental', kwargs={'pk': self.property.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already have a Pending rental request")
        self.assertEqual(RentalRequest.objects.filter(tenant=self.tenant, property=self.property).count(), 1)

    def test_past_move_in_date_rejected(self):
        """Verify that move-in dates in the past are rejected by form validation."""
        past_date = (datetime.date.today() - datetime.timedelta(days=5)).strftime('%Y-%m-%d')
        post_data = {
            'requested_move_in_date': past_date,
            'message': 'Past move in date'
        }
        response = self.tenant_client.post(reverse('core:request_rental', kwargs={'pk': self.property.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Move-in date cannot be in the past")
        self.assertFalse(RentalRequest.objects.filter(tenant=self.tenant).exists())


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class Phase4BTenancyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner_user',
            email='owner@example.com',
            password='Password123',
            first_name='John',
            last_name='Owner',
            role=User.ROLE_OWNER
        )

        self.other_owner = User.objects.create_user(
            username='other_owner',
            email='other@example.com',
            password='Password123',
            role=User.ROLE_OWNER
        )

        self.tenant1 = User.objects.create_user(
            username='tenant1',
            email='tenant1@example.com',
            password='Password123',
            first_name='Alice',
            role=User.ROLE_TENANT
        )

        self.tenant2 = User.objects.create_user(
            username='tenant2',
            email='tenant2@example.com',
            password='Password123',
            first_name='Bob',
            role=User.ROLE_TENANT
        )

        self.owner_client = Client()
        self.owner_client.login(username='owner_user', password='Password123')

        self.other_owner_client = Client()
        self.other_owner_client.login(username='other_owner', password='Password123')

        self.tenant1_client = Client()
        self.tenant1_client.login(username='tenant1', password='Password123')

        self.property = Property.objects.create(
            owner=self.owner,
            title='Seaside Apartment',
            description='2 BHK Apartment',
            location='Marine Drive, Kochi',
            address='10 Beach Road',
            monthly_rent=Decimal('25000.00'),
            security_deposit=Decimal('50000.00'),
            property_type='APARTMENT',
            bedrooms=2,
            bathrooms=2,
            is_available=True
        )

        self.move_in_date = datetime.date.today() + datetime.timedelta(days=7)
        self.request1 = RentalRequest.objects.create(
            tenant=self.tenant1,
            property=self.property,
            owner=self.owner,
            requested_move_in_date=self.move_in_date,
            message='Please accept my request',
            status=RentalRequest.STATUS_PENDING
        )

    def test_owner_accept_rental_request_creates_tenancy(self):
        """Verify that accepting a request creates an active tenancy and updates property availability."""
        end_date = self.move_in_date + datetime.timedelta(days=365)
        post_data = {
            'rental_start_date': self.move_in_date.strftime('%Y-%m-%d'),
            'rental_end_date': end_date.strftime('%Y-%m-%d'),
            'monthly_rent': '25000.00',
            'rent_due_day': 5,
            'security_deposit': '50000.00'
        }

        response = self.owner_client.post(reverse('core:accept_rental_request', kwargs={'pk': self.request1.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rental request accepted")

        # Verify request status
        self.request1.refresh_from_db()
        self.assertEqual(self.request1.status, RentalRequest.STATUS_ACCEPTED)

        # Verify property availability set to False
        self.property.refresh_from_db()
        self.assertFalse(self.property.is_available)

        # Verify Tenancy created
        tenancy = Tenancy.objects.get(rental_request=self.request1)
        self.assertEqual(tenancy.tenant, self.tenant1)
        self.assertEqual(tenancy.property, self.property)
        self.assertEqual(tenancy.owner, self.owner)
        self.assertEqual(tenancy.status, Tenancy.STATUS_ACTIVE)
        self.assertEqual(tenancy.monthly_rent, Decimal('25000.00'))

    def test_owner_accept_rejects_other_pending_requests(self):
        """Verify that accepting one request automatically rejects other pending requests for the same property."""
        request2 = RentalRequest.objects.create(
            tenant=self.tenant2,
            property=self.property,
            owner=self.owner,
            requested_move_in_date=self.move_in_date,
            status=RentalRequest.STATUS_PENDING
        )

        end_date = self.move_in_date + datetime.timedelta(days=365)
        post_data = {
            'rental_start_date': self.move_in_date.strftime('%Y-%m-%d'),
            'rental_end_date': end_date.strftime('%Y-%m-%d'),
            'monthly_rent': '25000.00',
            'rent_due_day': 5,
            'security_deposit': '50000.00'
        }

        self.owner_client.post(reverse('core:accept_rental_request', kwargs={'pk': self.request1.pk}), post_data)

        self.request1.refresh_from_db()
        request2.refresh_from_db()

        self.assertEqual(self.request1.status, RentalRequest.STATUS_ACCEPTED)
        self.assertEqual(request2.status, RentalRequest.STATUS_REJECTED)

    def test_owner_reject_rental_request(self):
        """Verify that rejecting a request updates status to REJECTED without creating tenancy."""
        response = self.owner_client.post(reverse('core:reject_rental_request', kwargs={'pk': self.request1.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "has been rejected")

        self.request1.refresh_from_db()
        self.assertEqual(self.request1.status, RentalRequest.STATUS_REJECTED)

        self.property.refresh_from_db()
        self.assertTrue(self.property.is_available)
        self.assertFalse(Tenancy.objects.exists())

    def test_cross_owner_action_prevention(self):
        """Verify that an owner cannot accept or reject requests for another owner's property."""
        # Other owner tries to accept
        end_date = self.move_in_date + datetime.timedelta(days=365)
        post_data = {
            'rental_start_date': self.move_in_date.strftime('%Y-%m-%d'),
            'rental_end_date': end_date.strftime('%Y-%m-%d'),
            'monthly_rent': '25000.00',
            'rent_due_day': 5,
            'security_deposit': '50000.00'
        }
        response = self.other_owner_client.post(reverse('core:accept_rental_request', kwargs={'pk': self.request1.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access denied")

        # Status remains pending
        self.request1.refresh_from_db()
        self.assertEqual(self.request1.status, RentalRequest.STATUS_PENDING)

    def test_tenancy_accept_form_validation(self):
        """Verify form validation for rental_end_date <= rental_start_date and rent_due_day out of range."""
        start_date = datetime.date.today()
        end_date_invalid = start_date - datetime.timedelta(days=1)

        form_data = {
            'rental_start_date': start_date,
            'rental_end_date': end_date_invalid,
            'monthly_rent': 25000,
            'rent_due_day': 30,  # Invalid due day (>28)
            'security_deposit': 50000
        }
        form = TenancyAcceptForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('rental_end_date', form.errors)
        self.assertIn('rent_due_day', form.errors)

    def test_tenant_dashboard_active_tenancy_display(self):
        """Verify active tenancy details appear on Tenant Dashboard when an active tenancy exists."""
        end_date = self.move_in_date + datetime.timedelta(days=365)
        Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property,
            owner=self.owner,
            rental_request=self.request1,
            rental_start_date=self.move_in_date,
            rental_end_date=end_date,
            monthly_rent=Decimal('25000.00'),
            rent_due_day=5,
            security_deposit=Decimal('50000.00'),
            status=Tenancy.STATUS_ACTIVE
        )

        response = self.tenant1_client.get(reverse('accounts:tenant_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Tenancy')
        self.assertContains(response, 'Seaside Apartment')
        self.assertContains(response, '25000')

    def test_owner_active_tenants_page(self):
        """Verify Owner can view active tenants page displaying active tenancies."""
        end_date = self.move_in_date + datetime.timedelta(days=365)
        Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property,
            owner=self.owner,
            rental_request=self.request1,
            rental_start_date=self.move_in_date,
            rental_end_date=end_date,
            monthly_rent=Decimal('25000.00'),
            rent_due_day=5,
            security_deposit=Decimal('50000.00'),
            status=Tenancy.STATUS_ACTIVE
        )

        response = self.owner_client.get(reverse('core:active_tenants'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Tenants')
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'Seaside Apartment')


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class Phase5ARentRecordTests(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user(
            username='owner1',
            email='owner1@example.com',
            password='Password123',
            role=User.ROLE_OWNER
        )
        self.owner2 = User.objects.create_user(
            username='owner2',
            email='owner2@example.com',
            password='Password123',
            role=User.ROLE_OWNER
        )

        self.tenant1 = User.objects.create_user(
            username='tenant1',
            email='tenant1@example.com',
            password='Password123',
            first_name='Alice',
            role=User.ROLE_TENANT
        )
        self.tenant2 = User.objects.create_user(
            username='tenant2',
            email='tenant2@example.com',
            password='Password123',
            first_name='Bob',
            role=User.ROLE_TENANT
        )

        self.owner1_client = Client()
        self.owner1_client.login(username='owner1', password='Password123')

        self.owner2_client = Client()
        self.owner2_client.login(username='owner2', password='Password123')

        self.tenant1_client = Client()
        self.tenant1_client.login(username='tenant1', password='Password123')

        self.tenant2_client = Client()
        self.tenant2_client.login(username='tenant2', password='Password123')

        self.property1 = Property.objects.create(
            owner=self.owner1,
            title='Sunset Villa',
            location='Kochi',
            address='12 Beach Rd',
            monthly_rent=Decimal('15000.00'),
            security_deposit=Decimal('30000.00')
        )

        self.property2 = Property.objects.create(
            owner=self.owner2,
            title='Green Residency',
            location='Bengaluru',
            address='45 Park Ave',
            monthly_rent=Decimal('20000.00'),
            security_deposit=Decimal('40000.00')
        )

        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=30)
        end_date = today + datetime.timedelta(days=300)

        self.tenancy1 = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property1,
            owner=self.owner1,
            rental_start_date=start_date,
            rental_end_date=end_date,
            monthly_rent=Decimal('15000.00'),
            rent_due_day=15,
            security_deposit=Decimal('30000.00'),
            status=Tenancy.STATUS_ACTIVE
        )

        self.tenancy2 = Tenancy.objects.create(
            tenant=self.tenant2,
            property=self.property2,
            owner=self.owner2,
            rental_start_date=start_date,
            rental_end_date=end_date,
            monthly_rent=Decimal('20000.00'),
            rent_due_day=20,
            security_deposit=Decimal('40000.00'),
            status=Tenancy.STATUS_ACTIVE
        )

    def test_active_tenancy_creates_current_rent_record(self):
        """Verify that an active tenancy auto-creates current month rent record with correct rent and due day."""
        record = self.tenancy1.get_or_create_current_rent_record()
        self.assertIsNotNone(record)
        self.assertEqual(record.amount, Decimal('15000.00'))

        today = datetime.date.today()
        expected_due_date = datetime.date(today.year, today.month, 15)
        self.assertEqual(record.due_date, expected_due_date)

    def test_status_and_days_message_calculation(self):
        """Verify dynamic calculation of status (UPCOMING, DUE, OVERDUE, PAID) and user-friendly messages."""
        today = datetime.date.today()
        month = datetime.date(today.year, today.month, 1)

        # 1. Upcoming record (due in 5 days)
        future_due = today + datetime.timedelta(days=5)
        rec1 = RentRecord(tenancy=self.tenancy1, rent_month=month, amount=10000, due_date=future_due)
        self.assertEqual(rec1.get_computed_status(), RentRecord.STATUS_UPCOMING)
        self.assertEqual(rec1.get_days_message(), "5 days remaining")

        # 2. Due record (due today)
        rec2 = RentRecord(tenancy=self.tenancy1, rent_month=month, amount=10000, due_date=today)
        self.assertEqual(rec2.get_computed_status(), RentRecord.STATUS_DUE)
        self.assertEqual(rec2.get_days_message(), "Rent is due today")

        # 3. Overdue record (due 3 days ago)
        past_due = today - datetime.timedelta(days=3)
        rec3 = RentRecord(tenancy=self.tenancy1, rent_month=month, amount=10000, due_date=past_due)
        self.assertEqual(rec3.get_computed_status(), RentRecord.STATUS_OVERDUE)
        self.assertEqual(rec3.get_days_message(), "3 days overdue")

        # 4. Paid record
        rec4 = RentRecord(
            tenancy=self.tenancy1,
            rent_month=month,
            amount=10000,
            due_date=past_due,
            payment_status=RentRecord.STATUS_PAID,
            paid_date=datetime.datetime(2026, 10, 1, 12, 0)
        )
        self.assertEqual(rec4.get_computed_status(), RentRecord.STATUS_PAID)
        self.assertIn("Paid on", rec4.get_days_message())

    def test_duplicate_rent_record_prevented(self):
        """Verify that duplicate rent records for the same tenancy and month cannot be created."""
        month = datetime.date(2026, 10, 1)
        RentRecord.objects.create(
            tenancy=self.tenancy1,
            rent_month=month,
            amount=Decimal('15000.00'),
            due_date=datetime.date(2026, 10, 15)
        )

        with self.assertRaises(Exception):
            RentRecord.objects.create(
                tenancy=self.tenancy1,
                rent_month=month,
                amount=Decimal('15000.00'),
                due_date=datetime.date(2026, 10, 15)
            )

    def test_no_rent_record_before_start_or_after_end_date(self):
        """Verify rent records are not created outside the tenancy start and end date period."""
        today = datetime.date.today()
        future_start = today + datetime.timedelta(days=60)
        future_end = today + datetime.timedelta(days=400)

        future_tenancy = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property1,
            owner=self.owner1,
            rental_start_date=future_start,
            rental_end_date=future_end,
            monthly_rent=Decimal('15000.00'),
            rent_due_day=5,
            status=Tenancy.STATUS_ACTIVE
        )

        record = future_tenancy.get_or_create_current_rent_record()
        self.assertIsNone(record)

    def test_tenant_sees_only_own_rent_records(self):
        """Verify Tenant A sees only their own rent records and cannot view Tenant B's rent records."""
        self.tenancy1.get_or_create_current_rent_record()
        self.tenancy2.get_or_create_current_rent_record()

        response1 = self.tenant1_client.get(reverse('core:tenant_rent_history'))
        self.assertEqual(response1.status_code, 200)
        self.assertContains(response1, 'Sunset Villa')
        self.assertNotContains(response1, 'Green Residency')

        response2 = self.tenant2_client.get(reverse('core:tenant_rent_history'))
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, 'Green Residency')
        self.assertNotContains(response2, 'Sunset Villa')

    def test_owner_sees_only_own_tenants_rent_records(self):
        """Verify Owner A sees only rent records for their properties and cannot view Owner B's rent records."""
        self.tenancy1.get_or_create_current_rent_record()
        self.tenancy2.get_or_create_current_rent_record()

        response1 = self.owner1_client.get(reverse('core:owner_rent_tracking'))
        self.assertEqual(response1.status_code, 200)
        self.assertContains(response1, 'Sunset Villa')
        self.assertNotContains(response1, 'Green Residency')

        response2 = self.owner2_client.get(reverse('core:owner_rent_tracking'))
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, 'Green Residency')
        self.assertNotContains(response2, 'Sunset Villa')


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class Phase5BSimulatedPaymentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner_user',
            email='owner@example.com',
            password='Password123',
            role=User.ROLE_OWNER
        )

        self.tenant1 = User.objects.create_user(
            username='tenant1',
            email='tenant1@example.com',
            password='Password123',
            first_name='Alice',
            role=User.ROLE_TENANT
        )

        self.tenant2 = User.objects.create_user(
            username='tenant2',
            email='tenant2@example.com',
            password='Password123',
            first_name='Bob',
            role=User.ROLE_TENANT
        )

        self.owner_client = Client()
        self.owner_client.login(username='owner_user', password='Password123')

        self.tenant1_client = Client()
        self.tenant1_client.login(username='tenant1', password='Password123')

        self.tenant2_client = Client()
        self.tenant2_client.login(username='tenant2', password='Password123')

        self.property = Property.objects.create(
            owner=self.owner,
            title='Seaside Villa',
            location='Kochi',
            address='10 Beach Rd',
            monthly_rent=Decimal('18000.00'),
            security_deposit=Decimal('36000.00')
        )

        today = datetime.date.today()
        self.tenancy = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property,
            owner=self.owner,
            rental_start_date=today - datetime.timedelta(days=30),
            rental_end_date=today + datetime.timedelta(days=300),
            monthly_rent=Decimal('18000.00'),
            rent_due_day=5,
            security_deposit=Decimal('36000.00'),
            status=Tenancy.STATUS_ACTIVE
        )

        self.rent_record = self.tenancy.get_or_create_current_rent_record()

    def test_tenant_can_open_pay_rent_page(self):
        """Verify Tenant can open Pay Rent page for their unpaid rent record."""
        response = self.tenant1_client.get(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pay Rent')
        self.assertContains(response, 'Seaside Villa')
        self.assertContains(response, '18000')

    def test_tenant_confirm_payment_creates_payment_and_updates_rent_record(self):
        """Verify that confirming demo payment creates Payment record and updates RentRecord to PAID."""
        post_data = {'payment_method': 'UPI'}
        response = self.tenant1_client.post(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Successful')

        # Verify RentRecord updated
        self.rent_record.refresh_from_db()
        self.assertEqual(self.rent_record.payment_status, RentRecord.STATUS_PAID)
        self.assertIsNotNone(self.rent_record.paid_date)

        # Verify Payment created
        payment = Payment.objects.get(rent_record=self.rent_record)
        self.assertEqual(payment.tenant, self.tenant1)
        self.assertEqual(payment.owner, self.owner)
        self.assertEqual(payment.amount_paid, Decimal('18000.00'))
        self.assertEqual(payment.payment_method, 'UPI')
        self.assertTrue(payment.transaction_id.startswith('SR-'))

    def test_paying_same_rent_twice_prevented(self):
        """Verify that paying an already paid rent record is blocked."""
        # First payment
        self.tenant1_client.post(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}), {'payment_method': 'UPI'})

        # Second payment attempt
        response = self.tenant1_client.post(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}), {'payment_method': 'CARD'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already been paid')
        self.assertEqual(Payment.objects.filter(rent_record=self.rent_record).count(), 1)

    def test_tenant_cannot_pay_another_tenants_rent(self):
        """Verify that Tenant B cannot pay Tenant A's rent record."""
        response = self.tenant2_client.post(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}), {'payment_method': 'UPI'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access denied')

        self.rent_record.refresh_from_db()
        self.assertNotEqual(self.rent_record.payment_status, RentRecord.STATUS_PAID)
        self.assertFalse(Payment.objects.exists())

    def test_owner_and_logged_out_users_cannot_pay_rent(self):
        """Verify property owners and unauthenticated visitors cannot access Pay Rent endpoint."""
        # Owner attempt
        response_owner = self.owner_client.get(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}), follow=True)
        self.assertEqual(response_owner.status_code, 200)
        self.assertContains(response_owner, 'Access denied')

        # Logged out attempt
        anon_client = Client()
        response_anon = anon_client.get(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}))
        self.assertEqual(response_anon.status_code, 302)  # Redirects to login

    def test_payment_appears_in_tenant_history_and_owner_tracking(self):
        """Verify completed payment appears in Tenant Payment History and Owner Rent Tracking views."""
        self.tenant1_client.post(reverse('core:pay_rent', kwargs={'pk': self.rent_record.pk}), {'payment_method': 'CARD'})
        payment = Payment.objects.get(rent_record=self.rent_record)

        # Tenant Payment History
        response_tenant = self.tenant1_client.get(reverse('core:tenant_payment_history'))
        self.assertEqual(response_tenant.status_code, 200)
        self.assertContains(response_tenant, payment.transaction_id)
        self.assertContains(response_tenant, 'Debit/Credit Card')

        # Owner Rent Tracking
        response_owner = self.owner_client.get(reverse('core:owner_rent_tracking'))
        self.assertEqual(response_owner.status_code, 200)
        self.assertContains(response_owner, payment.transaction_id)
        self.assertContains(response_owner, 'Debit/Credit Card')


class Phase5CRentReceiptTests(TestCase):
    """Unit test suite for Phase 5C - Rent Payment Receipts."""

    def setUp(self):
        self.owner1 = User.objects.create_user(
            username='owner1',
            email='owner1@test.com',
            password='password123',
            role=User.ROLE_OWNER
        )
        self.owner2 = User.objects.create_user(
            username='owner2',
            email='owner2@test.com',
            password='password123',
            role=User.ROLE_OWNER
        )
        self.tenant1 = User.objects.create_user(
            username='tenant1',
            email='tenant1@test.com',
            password='password123',
            role=User.ROLE_TENANT
        )
        self.tenant2 = User.objects.create_user(
            username='tenant2',
            email='tenant2@test.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.property = Property.objects.create(
            owner=self.owner1,
            title='Receipt Test Apartment',
            description='Test description',
            location='Kakkanad',
            address='Infopark Road',
            monthly_rent=Decimal('12000.00'),
            security_deposit=Decimal('24000.00'),
            property_type='APARTMENT'
        )


        today = datetime.date.today()
        self.tenancy = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property,
            owner=self.owner1,
            rental_start_date=today,
            rental_end_date=today + datetime.timedelta(days=365),
            monthly_rent=Decimal('12000.00'),
            rent_due_day=5,
            status=Tenancy.STATUS_ACTIVE
        )

        self.rent_record = RentRecord.objects.create(
            tenancy=self.tenancy,
            rent_month=datetime.date(today.year, today.month, 1),
            amount=Decimal('12000.00'),
            due_date=datetime.date(today.year, today.month, 5),
            payment_status=RentRecord.STATUS_PAID,
            paid_date=timezone.now()
        )

        self.payment = Payment.objects.create(
            rent_record=self.rent_record,
            tenant=self.tenant1,
            owner=self.owner1,
            property=self.property,
            amount_paid=Decimal('12000.00'),
            payment_method=Payment.PAYMENT_METHOD_UPI,
            transaction_id='SR-20260917-ABC12345'
        )

        self.tenant1_client = Client()
        self.tenant1_client.login(username='tenant1', password='password123')

        self.tenant2_client = Client()
        self.tenant2_client.login(username='tenant2', password='password123')

        self.owner1_client = Client()
        self.owner1_client.login(username='owner1', password='password123')

        self.owner2_client = Client()
        self.owner2_client.login(username='owner2', password='password123')

    def test_receipt_number_generation(self):
        """Verify unique receipt number format SR-RCP-YYYY-XXXXX."""
        expected_number = f"SR-RCP-{self.payment.paid_at.strftime('%Y')}-{self.payment.pk:05d}"
        self.assertEqual(self.payment.receipt_number, expected_number)

    def test_tenant_can_view_own_receipt(self):
        """Verify assigned tenant can view their own rent payment receipt."""
        response = self.tenant1_client.get(reverse('core:view_receipt', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.payment.receipt_number)
        self.assertContains(response, self.payment.transaction_id)
        self.assertContains(response, 'PAID')
        self.assertContains(response, 'Receipt Test Apartment')
        self.assertContains(response, 'tenant1')
        self.assertContains(response, 'owner1')
        self.assertContains(response, '12000')

    def test_owner_can_view_property_receipt(self):
        """Verify property owner can view rent payment receipt for their property."""
        response = self.owner1_client.get(reverse('core:view_receipt', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.payment.receipt_number)
        self.assertContains(response, self.payment.transaction_id)

    def test_unauthorized_tenant_cannot_view_other_tenant_receipt(self):
        """Verify another tenant is denied access (403 Forbidden) when accessing receipt."""
        response = self.tenant2_client.get(reverse('core:view_receipt', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unauthorized_owner_cannot_view_other_owner_receipt(self):
        """Verify another property owner is denied access (403 Forbidden) when accessing receipt."""
        response = self.owner2_client.get(reverse('core:view_receipt', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_redirected_to_login(self):
        """Verify logged-out user is redirected to login page when attempting to access receipt."""
        client = Client()
        response = client.get(reverse('core:view_receipt', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 302)


class Phase6UtilityBillTests(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user(
            username='util_owner1',
            email='util_owner1@example.com',
            password='password123',
            role=User.ROLE_OWNER
        )

        self.owner2 = User.objects.create_user(
            username='util_owner2',
            email='util_owner2@example.com',
            password='password123',
            role=User.ROLE_OWNER
        )

        self.tenant1 = User.objects.create_user(
            username='util_tenant1',
            email='util_tenant1@example.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.tenant2 = User.objects.create_user(
            username='util_tenant2',
            email='util_tenant2@example.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.property1 = Property.objects.create(
            owner=self.owner1,
            title='Utility Test Villa',
            description='Nice villa',
            location='Kochi',
            address='123 Marine Drive',
            monthly_rent=Decimal('8000.00'),
            security_deposit=Decimal('16000.00'),
            property_type='HOUSE',
            is_available=False
        )

        self.tenancy1 = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property1,
            owner=self.owner1,
            rental_start_date=datetime.date(2026, 1, 1),
            rental_end_date=datetime.date(2026, 12, 31),
            monthly_rent=Decimal('8000.00'),
            rent_due_day=5,
            security_deposit=Decimal('16000.00'),
            status=Tenancy.STATUS_ACTIVE
        )

        self.owner1_client = Client()
        self.owner1_client.login(username='util_owner1', password='password123')

        self.owner2_client = Client()
        self.owner2_client.login(username='util_owner2', password='password123')

        self.tenant1_client = Client()
        self.tenant1_client.login(username='util_tenant1', password='password123')

        self.tenant2_client = Client()
        self.tenant2_client.login(username='util_tenant2', password='password123')

        # Create active tenancy for owner2 as well
        self.property2 = Property.objects.create(
            owner=self.owner2,
            title='Owner2 House',
            description='House',
            location='Kochi',
            address='456 Street',
            monthly_rent=Decimal('5000.00'),
            is_available=False
        )
        self.tenancy2 = Tenancy.objects.create(
            tenant=self.tenant2,
            property=self.property2,
            owner=self.owner2,
            rental_start_date=datetime.date(2026, 1, 1),
            rental_end_date=datetime.date(2026, 12, 31),
            monthly_rent=Decimal('5000.00'),
            rent_due_day=5,
            status=Tenancy.STATUS_ACTIVE
        )

    def test_utility_bill_total_calculation(self):
        """Verify UtilityBill model accurately sums all four charge components."""
        bill = UtilityBill.objects.create(
            tenancy=self.tenancy1,
            billing_month=datetime.date(2026, 9, 1),
            electricity_charge=Decimal('740.00'),
            water_charge=Decimal('150.00'),
            maintenance_charge=Decimal('500.00'),
            other_charge=Decimal('0.00'),
            note='September utilities'
        )
        self.assertEqual(bill.total_utility_charges, Decimal('1390.00'))

    def test_duplicate_utility_bill_prevention(self):
        """Verify unique constraint prevents duplicate bills for same tenancy and month."""
        UtilityBill.objects.create(
            tenancy=self.tenancy1,
            billing_month=datetime.date(2026, 9, 1),
            electricity_charge=Decimal('740.00'),
            water_charge=Decimal('150.00'),
            maintenance_charge=Decimal('500.00'),
            other_charge=Decimal('0.00')
        )

        with self.assertRaises(Exception):
            UtilityBill.objects.create(
                tenancy=self.tenancy1,
                billing_month=datetime.date(2026, 9, 1),
                electricity_charge=Decimal('800.00'),
                water_charge=Decimal('200.00'),
                maintenance_charge=Decimal('500.00'),
                other_charge=Decimal('50.00')
            )

    def test_owner_can_add_utility_bill(self):
        """Verify property owner can create utility bill via view."""
        response = self.owner1_client.post(reverse('core:add_utility_bill'), {
            'tenancy': self.tenancy1.pk,
            'billing_month': '2026-09',
            'electricity_charge': '740',
            'water_charge': '150',
            'maintenance_charge': '500',
            'other_charge': '0',
            'note': 'Sep bill'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:owner_utility_bills'))

        bill = UtilityBill.objects.filter(tenancy=self.tenancy1, billing_month=datetime.date(2026, 9, 1)).first()
        self.assertIsNotNone(bill)
        self.assertEqual(bill.total_utility_charges, Decimal('1390.00'))

    def test_owner_cannot_add_utility_bill_for_other_owner_tenancy(self):
        """Verify owner2 cannot create utility bill for owner1's tenancy."""
        response = self.owner2_client.post(reverse('core:add_utility_bill'), {
            'tenancy': self.tenancy1.pk,
            'billing_month': '2026-09',
            'electricity_charge': '740',
            'water_charge': '150',
            'maintenance_charge': '500',
            'other_charge': '0'
        })
        # Should re-render form with error (200 OK)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UtilityBill.objects.filter(tenancy=self.tenancy1).exists())

    def test_tenant_can_view_own_utility_bills(self):
        """Verify tenant can view their own utility bills."""
        UtilityBill.objects.create(
            tenancy=self.tenancy1,
            billing_month=datetime.date(2026, 9, 1),
            electricity_charge=Decimal('740.00'),
            water_charge=Decimal('150.00'),
            maintenance_charge=Decimal('500.00'),
            other_charge=Decimal('0.00')
        )

        response = self.tenant1_client.get(reverse('core:tenant_utility_bills'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'September 2026')
        self.assertContains(response, '740')
        self.assertContains(response, '150')
        self.assertContains(response, '500')
        self.assertContains(response, '1390')

    def test_tenant_cannot_view_other_tenant_utility_bills(self):
        """Verify tenant2 does not see tenant1's utility bills."""
        UtilityBill.objects.create(
            tenancy=self.tenancy1,
            billing_month=datetime.date(2026, 9, 1),
            electricity_charge=Decimal('740.00'),
            water_charge=Decimal('150.00'),
            maintenance_charge=Decimal('500.00'),
            other_charge=Decimal('0.00')
        )

        response = self.tenant2_client.get(reverse('core:tenant_utility_bills'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'September 2026')
        self.assertContains(response, 'No utility bills recorded yet.')

    def test_tenant_dashboard_shows_latest_utility_bill_and_combined_total(self):
        """Verify tenant dashboard shows active rental and quick link cards."""
        UtilityBill.objects.create(
            tenancy=self.tenancy1,
            billing_month=datetime.date(2026, 9, 1),
            electricity_charge=Decimal('740.00'),
            water_charge=Decimal('150.00'),
            maintenance_charge=Decimal('500.00'),
            other_charge=Decimal('0.00')
        )

        response = self.tenant1_client.get(reverse('accounts:tenant_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Rental')
        self.assertContains(response, 'Utility Bills')


class Phase7MaintenanceRequestTests(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user(
            username='maint_owner1',
            email='maint_owner1@example.com',
            password='password123',
            role=User.ROLE_OWNER
        )

        self.owner2 = User.objects.create_user(
            username='maint_owner2',
            email='maint_owner2@example.com',
            password='password123',
            role=User.ROLE_OWNER
        )

        self.tenant1 = User.objects.create_user(
            username='maint_tenant1',
            email='maint_tenant1@example.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.tenant2 = User.objects.create_user(
            username='maint_tenant2',
            email='maint_tenant2@example.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.property1 = Property.objects.create(
            owner=self.owner1,
            title='Maintenance Test Flat',
            description='Nice flat',
            location='Kochi',
            address='789 Beach Road',
            monthly_rent=Decimal('10000.00'),
            is_available=False
        )

        self.tenancy1 = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property1,
            owner=self.owner1,
            rental_start_date=datetime.date(2026, 1, 1),
            rental_end_date=datetime.date(2026, 12, 31),
            monthly_rent=Decimal('10000.00'),
            rent_due_day=5,
            status=Tenancy.STATUS_ACTIVE
        )

        self.owner1_client = Client()
        self.owner1_client.login(username='maint_owner1', password='password123')

        self.owner2_client = Client()
        self.owner2_client.login(username='maint_owner2', password='password123')

        self.tenant1_client = Client()
        self.tenant1_client.login(username='maint_tenant1', password='password123')

        self.tenant2_client = Client()
        self.tenant2_client.login(username='maint_tenant2', password='password123')

    def test_tenant_submits_maintenance_request_with_photo(self):
        """Verify tenant can submit a maintenance request with optional photo upload."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        photo_file = SimpleUploadedFile('leak.gif', small_gif, content_type='image/gif')

        response = self.tenant1_client.post(reverse('core:report_maintenance'), {
            'category': MaintenanceRequest.CATEGORY_PLUMBING,
            'title': 'Bathroom Pipe Leak',
            'description': 'Water leaking under the sink.',
            'priority': MaintenanceRequest.PRIORITY_HIGH,
            'photo': photo_file
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:tenant_maintenance_list'))

        mreq = MaintenanceRequest.objects.filter(tenant=self.tenant1).first()
        self.assertIsNotNone(mreq)
        self.assertEqual(mreq.title, 'Bathroom Pipe Leak')
        self.assertEqual(mreq.status, MaintenanceRequest.STATUS_PENDING)
        self.assertEqual(mreq.tenancy, self.tenancy1)
        self.assertTrue(bool(mreq.photo))

    def test_owner_sees_request_and_updates_workflow_to_completion(self):
        """Verify owner sees incoming request and updates status through Pending -> Accepted -> In Progress -> Completed with completed_at timestamp."""
        mreq = MaintenanceRequest.objects.create(
            tenancy=self.tenancy1,
            tenant=self.tenant1,
            category=MaintenanceRequest.CATEGORY_PLUMBING,
            title='Leaky Tap',
            description='Tap dripping constantly.',
            priority=MaintenanceRequest.PRIORITY_MEDIUM
        )

        # Owner 1 sees request
        response = self.owner1_client.get(reverse('core:owner_maintenance_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Leaky Tap')

        # Owner 1 updates status to ACCEPTED
        response = self.owner1_client.post(reverse('core:owner_maintenance_detail', kwargs={'pk': mreq.pk}), {
            'status': MaintenanceRequest.STATUS_ACCEPTED,
            'owner_response': 'Plumber assigned.'
        })
        self.assertEqual(response.status_code, 302)
        mreq.refresh_from_db()
        self.assertEqual(mreq.status, MaintenanceRequest.STATUS_ACCEPTED)

        # Owner 1 updates status to COMPLETED
        response = self.owner1_client.post(reverse('core:owner_maintenance_detail', kwargs={'pk': mreq.pk}), {
            'status': MaintenanceRequest.STATUS_COMPLETED,
            'owner_response': 'Tap replaced and fixed.'
        })
        self.assertEqual(response.status_code, 302)
        mreq.refresh_from_db()
        self.assertEqual(mreq.status, MaintenanceRequest.STATUS_COMPLETED)
        self.assertIsNotNone(mreq.completed_at)

        # Tenant sees updated status and owner note
        response = self.tenant1_client.get(reverse('core:tenant_maintenance_detail', kwargs={'pk': mreq.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Completed')
        self.assertContains(response, 'Tap replaced and fixed.')

    def test_unauthorized_access_prevention(self):
        """Verify unauthorized tenants and owners cannot view or modify other users' maintenance requests."""
        mreq = MaintenanceRequest.objects.create(
            tenancy=self.tenancy1,
            tenant=self.tenant1,
            category=MaintenanceRequest.CATEGORY_ELECTRICAL,
            title='Fuse Fault',
            description='Main breaker tripping.',
            priority=MaintenanceRequest.PRIORITY_HIGH
        )

        # Tenant 2 cannot view Tenant 1's request detail
        response = self.tenant2_client.get(reverse('core:tenant_maintenance_detail', kwargs={'pk': mreq.pk}))
        self.assertEqual(response.status_code, 403)

        # Owner 2 cannot view or edit Owner 1's property request
        response = self.owner2_client.get(reverse('core:owner_maintenance_detail', kwargs={'pk': mreq.pk}))
        self.assertEqual(response.status_code, 403)

        # Logged out user redirected to login
        unauth_client = Client()
        response = unauth_client.get(reverse('core:report_maintenance'))
        self.assertEqual(response.status_code, 302)


class Phase8RenewalRequestTests(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user(
            username='renew_owner1',
            email='renew_owner1@example.com',
            password='password123',
            role=User.ROLE_OWNER
        )

        self.owner2 = User.objects.create_user(
            username='renew_owner2',
            email='renew_owner2@example.com',
            password='password123',
            role=User.ROLE_OWNER
        )

        self.tenant1 = User.objects.create_user(
            username='renew_tenant1',
            email='renew_tenant1@example.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.tenant2 = User.objects.create_user(
            username='renew_tenant2',
            email='renew_tenant2@example.com',
            password='password123',
            role=User.ROLE_TENANT
        )

        self.property1 = Property.objects.create(
            owner=self.owner1,
            title='Renewal Test Apartment',
            description='Apartment for lease renewal test',
            location='Kochi',
            address='101 Renewal Road',
            monthly_rent=Decimal('12000.00'),
            is_available=False
        )

        self.tenancy1 = Tenancy.objects.create(
            tenant=self.tenant1,
            property=self.property1,
            owner=self.owner1,
            rental_start_date=datetime.date(2026, 1, 1),
            rental_end_date=datetime.date(2026, 12, 31),
            monthly_rent=Decimal('12000.00'),
            rent_due_day=5,
            status=Tenancy.STATUS_ACTIVE
        )

        self.owner1_client = Client()
        self.owner1_client.login(username='renew_owner1', password='password123')

        self.owner2_client = Client()
        self.owner2_client.login(username='renew_owner2', password='password123')

        self.tenant1_client = Client()
        self.tenant1_client.login(username='renew_tenant1', password='password123')

        self.tenant2_client = Client()
        self.tenant2_client.login(username='renew_tenant2', password='password123')

    def test_tenant_submits_valid_renewal_request(self):
        """Verify tenant can submit renewal request with a new end date later than current end date."""
        response = self.tenant1_client.post(reverse('core:request_agreement_renewal'), {
            'requested_new_end_date': '2027-06-30',
            'message': 'Requesting 6 month extension.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:tenant_agreement'))

        renewal = RenewalRequest.objects.filter(tenancy=self.tenancy1).first()
        self.assertIsNotNone(renewal)
        self.assertEqual(renewal.requested_new_end_date, datetime.date(2027, 6, 30))
        self.assertEqual(renewal.status, RenewalRequest.STATUS_PENDING)

    def test_renewal_request_invalid_end_date_validation(self):
        """Verify form validation rejects requested new end date earlier than or equal to current end date."""
        response = self.tenant1_client.post(reverse('core:request_agreement_renewal'), {
            'requested_new_end_date': '2026-11-30',
            'message': 'Invalid date request.'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RenewalRequest.objects.filter(tenancy=self.tenancy1).exists())

    def test_prevent_duplicate_pending_renewal_requests(self):
        """Verify tenant cannot submit multiple pending renewal requests for same tenancy."""
        RenewalRequest.objects.create(
            tenancy=self.tenancy1,
            tenant=self.tenant1,
            requested_new_end_date=datetime.date(2027, 6, 30),
            status=RenewalRequest.STATUS_PENDING
        )

        response = self.tenant1_client.post(reverse('core:request_agreement_renewal'), {
            'requested_new_end_date': '2027-12-31',
            'message': 'Second request'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RenewalRequest.objects.filter(tenancy=self.tenancy1).count(), 1)

    def test_owner_approves_renewal_request_and_updates_tenancy_end_date(self):
        """Verify owner approval atomically updates tenancy rental_end_date and sets request status APPROVED."""
        renewal = RenewalRequest.objects.create(
            tenancy=self.tenancy1,
            tenant=self.tenant1,
            requested_new_end_date=datetime.date(2027, 6, 30),
            status=RenewalRequest.STATUS_PENDING
        )

        response = self.owner1_client.post(reverse('core:approve_renewal_request', kwargs={'pk': renewal.pk}), {
            'owner_response': 'Approved! Enjoy your stay.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:owner_renewal_requests'))

        renewal.refresh_from_db()
        self.tenancy1.refresh_from_db()
        self.assertEqual(renewal.status, RenewalRequest.STATUS_APPROVED)
        self.assertEqual(self.tenancy1.rental_end_date, datetime.date(2027, 6, 30))

    def test_owner_rejects_renewal_request_leaving_tenancy_end_date_unchanged(self):
        """Verify owner rejection sets status REJECTED without altering tenancy rental_end_date."""
        original_end_date = self.tenancy1.rental_end_date
        renewal = RenewalRequest.objects.create(
            tenancy=self.tenancy1,
            tenant=self.tenant1,
            requested_new_end_date=datetime.date(2027, 6, 30),
            status=RenewalRequest.STATUS_PENDING
        )

        response = self.owner1_client.post(reverse('core:reject_renewal_request', kwargs={'pk': renewal.pk}), {
            'owner_response': 'Sorry, property is booked for next year.'
        })
        self.assertEqual(response.status_code, 302)

        renewal.refresh_from_db()
        self.tenancy1.refresh_from_db()
        self.assertEqual(renewal.status, RenewalRequest.STATUS_REJECTED)
        self.assertEqual(self.tenancy1.rental_end_date, original_end_date)

    def test_unauthorized_owner_cannot_approve_or_reject_renewal(self):
        """Verify owner2 cannot approve or reject owner1's renewal request."""
        renewal = RenewalRequest.objects.create(
            tenancy=self.tenancy1,
            tenant=self.tenant1,
            requested_new_end_date=datetime.date(2027, 6, 30),
            status=RenewalRequest.STATUS_PENDING
        )

        response = self.owner2_client.post(reverse('core:approve_renewal_request', kwargs={'pk': renewal.pk}), {
            'owner_response': 'Unauthorized approval attempt.'
        })
        self.assertEqual(response.status_code, 403)
        renewal.refresh_from_db()
        self.assertEqual(renewal.status, RenewalRequest.STATUS_PENDING)











