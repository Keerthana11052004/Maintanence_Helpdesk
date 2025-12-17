#!/usr/bin/env python3
"""
Comprehensive test script for Maintenance Help Desk System
Tests all screens and functionality
"""

import requests
import json
from bs4 import BeautifulSoup
from app import app, db, User, ProductionMachine, Electrical

class MaintenanceHelpDeskTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.admin_credentials = {
            'email': 'admin@maintenance.com',
            'password': 'admin123'
        }
        self.user_credentials = {
            'email': 'john.doe@company.com',
            'password': 'user123'
        }
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

    def test_login_page(self):
        """Test login page accessibility"""
        try:
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                form = soup.find('form')
                if form and form.get('method') == 'POST':
                    self.log_test("Login Page", True, "Form found and accessible")
                    return True
                else:
                    self.log_test("Login Page", False, "Form not found or incorrect method")
                    return False
            else:
                self.log_test("Login Page", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Login Page", False, str(e))
            return False

    def test_admin_login(self):
        """Test admin login functionality"""
        try:
            # Get login page first
            login_page = self.session.get(f"{self.base_url}/login")
            if login_page.status_code != 200:
                self.log_test("Admin Login", False, "Cannot access login page")
                return False

            # Attempt login
            login_data = self.admin_credentials
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            if response.status_code == 302:  # Redirect after successful login
                self.log_test("Admin Login", True, "Redirected after login")
                return True
            elif response.status_code == 200:
                # Check if we're still on login page (failed login)
                if "login" in response.url.lower():
                    self.log_test("Admin Login", False, "Still on login page - credentials may be wrong")
                    return False
                else:
                    self.log_test("Admin Login", True, "Login successful")
                    return True
            else:
                self.log_test("Admin Login", False, f"Unexpected status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Login", False, str(e))
            return False

    def test_user_login(self):
        """Test user login functionality"""
        try:
            # Create new session for user login
            user_session = requests.Session()
            
            # Get login page first
            login_page = user_session.get(f"{self.base_url}/login")
            if login_page.status_code != 200:
                self.log_test("User Login", False, "Cannot access login page")
                return False

            # Attempt login
            login_data = self.user_credentials
            response = user_session.post(f"{self.base_url}/login", data=login_data)
            
            if response.status_code == 302:  # Redirect after successful login
                self.log_test("User Login", True, "Redirected after login")
                return True
            elif response.status_code == 200:
                if "login" in response.url.lower():
                    self.log_test("User Login", False, "Still on login page - credentials may be wrong")
                    return False
                else:
                    self.log_test("User Login", True, "Login successful")
                    return True
            else:
                self.log_test("User Login", False, f"Unexpected status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("User Login", False, str(e))
            return False

    def test_admin_dashboard(self):
        """Test admin dashboard"""
        try:
            # First login as admin
            login_data = self.admin_credentials
            self.session.post(f"{self.base_url}/login", data=login_data)
            
            # Access dashboard
            response = self.session.get(f"{self.base_url}/dashboard")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Check for admin-specific elements
                if "Admin Dashboard" in response.text and "Production Machine Tickets" in response.text:
                    self.log_test("Admin Dashboard", True, "Admin dashboard loaded correctly")
                    return True
                else:
                    self.log_test("Admin Dashboard", False, "Admin dashboard content not found")
                    return False
            else:
                self.log_test("Admin Dashboard", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Dashboard", False, str(e))
            return False

    def test_user_dashboard(self):
        """Test user dashboard"""
        try:
            # Create new session for user
            user_session = requests.Session()
            
            # Login as user
            login_data = self.user_credentials
            user_session.post(f"{self.base_url}/login", data=login_data)
            
            # Access dashboard
            response = user_session.get(f"{self.base_url}/dashboard")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Check for user-specific elements
                if "Raise Production Machine Ticket" in response.text and "Raise Electrical Ticket" in response.text:
                    self.log_test("User Dashboard", True, "User dashboard loaded correctly")
                    return True
                else:
                    self.log_test("User Dashboard", False, "User dashboard content not found")
                    return False
            else:
                self.log_test("User Dashboard", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("User Dashboard", False, str(e))
            return False

    def test_ticket_creation_pages(self):
        """Test ticket creation pages"""
        try:
            # Login as user first
            user_session = requests.Session()
            login_data = self.user_credentials
            user_session.post(f"{self.base_url}/login", data=login_data)
            
            # Test production ticket page
            response = user_session.get(f"{self.base_url}/raise_ticket/production")
            if response.status_code == 200 and "Raise Production Machine Ticket" in response.text:
                self.log_test("Production Ticket Page", True, "Page accessible")
            else:
                self.log_test("Production Ticket Page", False, f"HTTP {response.status_code}")
                return False
            
            # Test electrical ticket page
            response = user_session.get(f"{self.base_url}/raise_ticket/electrical")
            if response.status_code == 200 and "Raise Electrical Ticket" in response.text:
                self.log_test("Electrical Ticket Page", True, "Page accessible")
                return True
            else:
                self.log_test("Electrical Ticket Page", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Ticket Creation Pages", False, str(e))
            return False

    def test_admin_management_pages(self):
        """Test admin management pages"""
        try:
            # Login as admin first
            login_data = self.admin_credentials
            self.session.post(f"{self.base_url}/login", data=login_data)
            
            # Test admin production page
            response = self.session.get(f"{self.base_url}/admin/production")
            if response.status_code == 200 and "Production Machine Tickets" in response.text:
                self.log_test("Admin Production Page", True, "Page accessible")
            else:
                self.log_test("Admin Production Page", False, f"HTTP {response.status_code}")
                return False
            
            # Test admin electrical page
            response = self.session.get(f"{self.base_url}/admin/electrical")
            if response.status_code == 200 and "Electrical Tickets" in response.text:
                self.log_test("Admin Electrical Page", True, "Page accessible")
            else:
                self.log_test("Admin Electrical Page", False, f"HTTP {response.status_code}")
                return False
            
            # Test add user page
            response = self.session.get(f"{self.base_url}/admin/add_user")
            if response.status_code == 200 and "Add New User" in response.text:
                self.log_test("Add User Page", True, "Page accessible")
                return True
            else:
                self.log_test("Add User Page", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Management Pages", False, str(e))
            return False

    def test_database_functionality(self):
        """Test database operations"""
        try:
            with app.app_context():
                # Test user queries
                admin_count = User.query.filter_by(role='manager').count()
                user_count = User.query.filter_by(role='user').count()
                
                if admin_count > 0 and user_count > 0:
                    self.log_test("Database Users", True, f"Found {admin_count} admins, {user_count} users")
                else:
                    self.log_test("Database Users", False, "No users found in database")
                    return False
                
                # Test ticket queries
                prod_tickets = ProductionMachine.query.count()
                elec_tickets = Electrical.query.count()
                
                self.log_test("Database Tickets", True, f"Found {prod_tickets} production, {elec_tickets} electrical tickets")
                return True
        except Exception as e:
            self.log_test("Database Functionality", False, str(e))
            return False

    def test_static_files(self):
        """Test static file accessibility"""
        try:
            # Test CSS file
            response = requests.get(f"{self.base_url}/static/css/style.css")
            if response.status_code == 200:
                self.log_test("CSS File", True, "CSS file accessible")
            else:
                self.log_test("CSS File", False, f"HTTP {response.status_code}")
                return False
            
            # Test JS file
            response = requests.get(f"{self.base_url}/static/js/main.js")
            if response.status_code == 200:
                self.log_test("JS File", True, "JS file accessible")
                return True
            else:
                self.log_test("JS File", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Static Files", False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Comprehensive Maintenance Help Desk Test Suite")
        print("=" * 60)
        
        tests = [
            ("Login Page", self.test_login_page),
            ("Admin Login", self.test_admin_login),
            ("User Login", self.test_user_login),
            ("Admin Dashboard", self.test_admin_dashboard),
            ("User Dashboard", self.test_user_dashboard),
            ("Ticket Creation Pages", self.test_ticket_creation_pages),
            ("Admin Management Pages", self.test_admin_management_pages),
            ("Database Functionality", self.test_database_functionality),
            ("Static Files", self.test_static_files)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            if test_func():
                passed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! System is working correctly.")
        else:
            print("⚠️  Some tests failed. Issues found:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        return passed == total

def main():
    tester = MaintenanceHelpDeskTester()
    return tester.run_all_tests()

if __name__ == '__main__':
    main()






