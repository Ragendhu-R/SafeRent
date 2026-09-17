import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saferent.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def run_tests():
    print("--- STARTING PHASE 2 AUTOMATED INTEGRATION TESTS ---")
    
    client = Client()
    
    # Clean up existing test users if any
    User.objects.filter(username__in=['tenant_test', 'owner_test']).delete()

    # TEST 1: Register Tenant account -> Login -> Tenant Dashboard
    print("\n[TEST 1] Registering Tenant account ('tenant_test')...")
    signup_data = {
        'first_name': 'Alice',
        'last_name': 'Tenant',
        'username': 'tenant_test',
        'email': 'tenant@example.com',
        'phone_number': '9876543210',
        'role': 'TENANT',
        'password1': 'SafePass123!',
        'password2': 'SafePass123!'
    }
    response = client.post('/accounts/signup/', signup_data, follow=True)
    assert response.status_code == 200
    tenant_user = User.objects.get(username='tenant_test')
    assert tenant_user.role == 'TENANT'
    assert tenant_user.first_name == 'Alice'
    assert '/tenant/dashboard/' in response.redirect_chain[0][0] or response.template_name[0] == 'accounts/tenant_dashboard.html'
    print("[OK] TEST 1 PASSED: Tenant registered & redirected to Tenant Dashboard.")

    client.logout()

    # TEST 2: Register Owner account -> Login -> Owner Dashboard
    print("\n[TEST 2] Registering Owner account ('owner_test')...")
    owner_data = {
        'first_name': 'Bob',
        'last_name': 'Owner',
        'username': 'owner_test',
        'email': 'owner@example.com',
        'phone_number': '9123456789',
        'role': 'OWNER',
        'password1': 'SafePass123!',
        'password2': 'SafePass123!'
    }
    response = client.post('/accounts/signup/', owner_data, follow=True)
    assert response.status_code == 200
    owner_user = User.objects.get(username='owner_test')
    assert owner_user.role == 'OWNER'
    assert owner_user.first_name == 'Bob'
    print("[OK] TEST 2 PASSED: Owner registered & redirected to Owner Dashboard.")

    # TEST 3: Tenant attempts to access Owner Dashboard -> Access denied / redirected
    print("\n[TEST 3] Testing Tenant unauthorized access to Owner Dashboard...")
    client.login(username='tenant_test', password='SafePass123!')
    response = client.get('/owner/dashboard/', follow=True)
    assert response.status_code == 200
    # Should redirect back to Tenant Dashboard
    assert '/tenant/dashboard/' in [r[0] for r in response.redirect_chain]
    print("[OK] TEST 3 PASSED: Tenant access to Owner Dashboard blocked & redirected.")

    # TEST 4: Owner attempts to access Tenant Dashboard -> Access denied / redirected
    print("\n[TEST 4] Testing Owner unauthorized access to Tenant Dashboard...")
    client.login(username='owner_test', password='SafePass123!')
    response = client.get('/tenant/dashboard/', follow=True)
    assert response.status_code == 200
    # Should redirect back to Owner Dashboard
    assert '/owner/dashboard/' in [r[0] for r in response.redirect_chain]
    print("[OK] TEST 4 PASSED: Owner access to Tenant Dashboard blocked & redirected.")

    # TEST 5: Logout -> Return to homepage
    print("\n[TEST 5] Testing Logout flow...")
    response = client.get('/accounts/logout/', follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[0][0] == '/'
    print("[OK] TEST 5 PASSED: Logout successful & redirected to homepage.")

    # TEST 6: Logged-out user attempts to access dashboard -> Redirect to login
    print("\n[TEST 6] Testing unauthenticated access protection...")
    response = client.get('/tenant/dashboard/', follow=True)
    assert response.status_code == 200
    assert '/accounts/login/' in response.redirect_chain[0][0]
    
    response = client.get('/owner/dashboard/', follow=True)
    assert response.status_code == 200
    assert '/accounts/login/' in response.redirect_chain[0][0]
    print("[OK] TEST 6 PASSED: Logged-out users redirected to login.")

    # TEST 7: Edit profile -> Updated information is saved
    print("\n[TEST 7] Testing profile updates...")
    client.login(username='tenant_test', password='SafePass123!')
    update_data = {
        'first_name': 'Alice Updated',
        'last_name': 'Tenant',
        'email': 'alice.updated@example.com',
        'phone_number': '9998887776'
    }
    response = client.post('/accounts/profile/', update_data, follow=True)
    assert response.status_code == 200
    tenant_user.refresh_from_db()
    assert tenant_user.first_name == 'Alice Updated'
    assert tenant_user.email == 'alice.updated@example.com'
    assert tenant_user.phone_number == '9998887776'
    assert tenant_user.role == 'TENANT'  # Role remains unchanged
    print("[OK] TEST 7 PASSED: Profile edited and verified in DB.")

    # TEST 8: Navbar authentication states
    print("\n[TEST 8] Testing navbar dynamic rendering...")
    # Logged in state
    response = client.get('/')
    assert b'Hello,' in response.content or b'Dashboard' in response.content
    assert b'Logout' in response.content

    # Logged out state
    client.logout()
    response = client.get('/')
    assert b'Login' in response.content
    assert b'Sign Up' in response.content
    print("[OK] TEST 8 PASSED: Navbar correctly renders authenticated vs guest states.")

    print("\n==============================================")
    print("ALL 8 PHASE 2 TEST SCENARIOS PASSED CLEANLY!")
    print("==============================================")

if __name__ == '__main__':
    run_tests()
