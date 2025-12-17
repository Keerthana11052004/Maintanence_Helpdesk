#!/usr/bin/env python3
"""
Functional test script for Maintenance Help Desk System
Tests actual ticket creation, editing, and management workflows
"""

import requests
import json
from bs4 import BeautifulSoup
from app import app, db, User, ProductionMachine, Electrical

class FunctionalTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.user_session = requests.Session()
        self.admin_session = requests.Session()
        self.test_results = []

    def log_test(self, test_name, success, message=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })

    def setup_sessions(self):
        """Setup user and admin sessions"""
        try:
            # Login as user
            user_login_data = {
                'email': 'john.doe@company.com',
                'password': 'user123'
            }
            response = self.user_session.post(f"{self.base_url}/login", data=user_login_data)
            if response.status_code not in [200, 302]:
                self.log_test("User Session Setup", False, f"HTTP {response.status_code}")
                return False

            # Login as admin
            admin_login_data = {
                'email': 'admin@maintenance.com',
                'password': 'admin123'
            }
            response = self.admin_session.post(f"{self.base_url}/login", data=admin_login_data)
            if response.status_code not in [200, 302]:
                self.log_test("Admin Session Setup", False, f"HTTP {response.status_code}")
                return False

            self.log_test("Session Setup", True, "Both user and admin sessions created")
            return True
        except Exception as e:
            self.log_test("Session Setup", False, str(e))
            return False

    def test_create_production_ticket(self):
        """Test creating a production machine ticket"""
        try:
            # Get the ticket creation page
            response = self.user_session.get(f"{self.base_url}/raise_ticket/production")
            if response.status_code != 200:
                self.log_test("Create Production Ticket", False, f"Cannot access page: {response.status_code}")
                return False

            # Create a ticket
            ticket_data = {
                'machine_name': 'Test Machine - Functional Test',
                'issue_description': 'This is a test ticket created during functional testing. Machine is not working properly.',
                'priority': 'high'
            }
            
            response = self.user_session.post(f"{self.base_url}/raise_ticket/production", data=ticket_data, allow_redirects=False)
            if response.status_code == 302:  # Redirect after successful creation
                self.log_test("Create Production Ticket", True, "Ticket created successfully")
                return True
            elif response.status_code == 200 and "my_tickets/production" in response.url:
                self.log_test("Create Production Ticket", True, "Ticket created and redirected")
                return True
            else:
                self.log_test("Create Production Ticket", False, f"Unexpected response: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create Production Ticket", False, str(e))
            return False

    def test_create_electrical_ticket(self):
        """Test creating an electrical ticket"""
        try:
            # Get the ticket creation page
            response = self.user_session.get(f"{self.base_url}/raise_ticket/electrical")
            if response.status_code != 200:
                self.log_test("Create Electrical Ticket", False, f"Cannot access page: {response.status_code}")
                return False

            # Create a ticket
            ticket_data = {
                'equipment_name': 'Test Electrical Equipment - Functional Test',
                'issue_description': 'This is a test electrical ticket created during functional testing. Equipment needs repair.',
                'priority': 'medium'
            }
            
            response = self.user_session.post(f"{self.base_url}/raise_ticket/electrical", data=ticket_data, allow_redirects=False)
            if response.status_code == 302:  # Redirect after successful creation
                self.log_test("Create Electrical Ticket", True, "Ticket created successfully")
                return True
            elif response.status_code == 200 and "my_tickets/electrical" in response.url:
                self.log_test("Create Electrical Ticket", True, "Ticket created and redirected")
                return True
            else:
                self.log_test("Create Electrical Ticket", False, f"Unexpected response: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create Electrical Ticket", False, str(e))
            return False

    def test_view_user_tickets(self):
        """Test viewing user tickets"""
        try:
            # Test production tickets view
            response = self.user_session.get(f"{self.base_url}/my_tickets/production")
            if response.status_code == 200 and "My Production Machine Tickets" in response.text:
                self.log_test("View Production Tickets", True, "Page loaded correctly")
            else:
                self.log_test("View Production Tickets", False, f"HTTP {response.status_code}")
                return False

            # Test electrical tickets view
            response = self.user_session.get(f"{self.base_url}/my_tickets/electrical")
            if response.status_code == 200 and "My Electrical Tickets" in response.text:
                self.log_test("View Electrical Tickets", True, "Page loaded correctly")
                return True
            else:
                self.log_test("View Electrical Tickets", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("View User Tickets", False, str(e))
            return False

    def test_admin_view_tickets(self):
        """Test admin viewing all tickets"""
        try:
            # Test admin production tickets view
            response = self.admin_session.get(f"{self.base_url}/admin/production")
            if response.status_code == 200 and "Production Machine Tickets" in response.text:
                self.log_test("Admin View Production Tickets", True, "Page loaded correctly")
            else:
                self.log_test("Admin View Production Tickets", False, f"HTTP {response.status_code}")
                return False

            # Test admin electrical tickets view
            response = self.admin_session.get(f"{self.base_url}/admin/electrical")
            if response.status_code == 200 and "Electrical Tickets" in response.text:
                self.log_test("Admin View Electrical Tickets", True, "Page loaded correctly")
                return True
            else:
                self.log_test("Admin View Electrical Tickets", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin View Tickets", False, str(e))
            return False

    def test_create_new_user(self):
        """Test admin creating a new user"""
        try:
            # Get the add user page
            response = self.admin_session.get(f"{self.base_url}/admin/add_user")
            if response.status_code != 200:
                self.log_test("Create New User", False, f"Cannot access page: {response.status_code}")
                return False

            # Create a new user with unique email
            import time
            unique_email = f'testuser{int(time.time())}@functional.com'
            user_data = {
                'name': 'Test User - Functional Test',
                'email': unique_email,
                'password': 'testpass123',
                'unit': 'Test Unit',
                'role': 'user'
            }
            
            response = self.admin_session.post(f"{self.base_url}/admin/add_user", data=user_data, allow_redirects=False)
            if response.status_code == 302:  # Redirect after successful creation
                location = response.headers.get('Location', '')
                if 'dashboard' in location:
                    self.log_test("Create New User", True, "User created successfully")
                    return True
                else:
                    self.log_test("Create New User", False, f"Redirected to unexpected location: {location}")
                    return False
            else:
                self.log_test("Create New User", False, f"Unexpected response: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create New User", False, str(e))
            return False

    def test_logout_functionality(self):
        """Test logout functionality"""
        try:
            # Test user logout
            response = self.user_session.get(f"{self.base_url}/logout", allow_redirects=False)
            if response.status_code == 302:  # Redirect after logout
                self.log_test("User Logout", True, "User logged out successfully")
            else:
                self.log_test("User Logout", False, f"Unexpected response: {response.status_code}")
                return False

            # Test admin logout
            response = self.admin_session.get(f"{self.base_url}/logout", allow_redirects=False)
            if response.status_code == 302:  # Redirect after logout
                self.log_test("Admin Logout", True, "Admin logged out successfully")
                return True
            else:
                self.log_test("Admin Logout", False, f"Unexpected response: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Logout Functionality", False, str(e))
            return False

    def test_database_verification(self):
        """Verify data was created in database"""
        try:
            with app.app_context():
                # Check if new tickets were created
                prod_tickets = ProductionMachine.query.filter(
                    ProductionMachine.machine_name.contains('Functional Test')
                ).count()
                
                elec_tickets = Electrical.query.filter(
                    Electrical.equipment_name.contains('Functional Test')
                ).count()
                
                if prod_tickets > 0 and elec_tickets > 0:
                    self.log_test("Database Verification", True, f"Found {prod_tickets} production and {elec_tickets} electrical test tickets")
                else:
                    self.log_test("Database Verification", False, "Test tickets not found in database")
                    return False

                # Check if new user was created (check for any test user)
                new_user = User.query.filter(User.email.like('testuser%@functional.com')).first()
                if new_user:
                    self.log_test("New User Verification", True, f"New user found: {new_user.name}")
                    return True
                else:
                    self.log_test("New User Verification", False, "New user not found in database")
                    return False
        except Exception as e:
            self.log_test("Database Verification", False, str(e))
            return False

    def run_functional_tests(self):
        """Run all functional tests"""
        print("🔧 Functional Testing - Maintenance Help Desk System")
        print("=" * 60)
        
        # Setup sessions first
        if not self.setup_sessions():
            print("❌ Cannot proceed without proper session setup")
            return False

        tests = [
            ("Create Production Ticket", self.test_create_production_ticket),
            ("Create Electrical Ticket", self.test_create_electrical_ticket),
            ("View User Tickets", self.test_view_user_tickets),
            ("Admin View Tickets", self.test_admin_view_tickets),
            ("Create New User", self.test_create_new_user),
            ("Logout Functionality", self.test_logout_functionality),
            ("Database Verification", self.test_database_verification)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            if test_func():
                passed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Functional Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All functional tests passed! System is working correctly.")
        else:
            print("⚠️  Some functional tests failed:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        return passed == total

def main():
    tester = FunctionalTester()
    return tester.run_functional_tests()

if __name__ == '__main__':
    main()
