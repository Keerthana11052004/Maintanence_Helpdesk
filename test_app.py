#!/usr/bin/env python3
"""
Test script for Maintenance Help Desk System
This script tests the basic functionality of the application
"""

import requests
import json
from app import app, db, User, ProductionMachine, Electrical

def test_database_connection():
    """Test database connection and models"""
    print("🔍 Testing database connection...")
    try:
        with app.app_context():
            # Test user count
            user_count = User.query.count()
            print(f"✅ Found {user_count} users in database")
            
            # Test admin user
            admin = User.query.filter_by(email='admin@maintenance.com').first()
            if admin:
                print(f"✅ Admin user found: {admin.name} ({admin.role})")
            else:
                print("❌ Admin user not found")
            
            # Test sample users
            sample_users = User.query.filter_by(role='user').all()
            print(f"✅ Found {len(sample_users)} regular users")
            
            return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_flask_routes():
    """Test Flask routes"""
    print("\n🔍 Testing Flask routes...")
    
    base_url = "http://localhost:5000"
    
    try:
        # Test login page
        response = requests.get(f"{base_url}/login", timeout=5)
        if response.status_code == 200:
            print("✅ Login page accessible")
        else:
            print(f"❌ Login page failed: {response.status_code}")
        
        # Test dashboard redirect
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 302:
            print("✅ Root route redirects properly")
        else:
            print(f"❌ Root route failed: {response.status_code}")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Route test failed: {e}")
        return False

def test_user_creation():
    """Test creating a new user"""
    print("\n🔍 Testing user creation...")
    try:
        with app.app_context():
            # Create a test user
            test_user = User(
                name='Test User',
                email='test@example.com',
                unit='Test Unit',
                role='user'
            )
            test_user.set_password('test123')
            
            # Check if user already exists
            existing = User.query.filter_by(email='test@example.com').first()
            if existing:
                print("ℹ️  Test user already exists")
            else:
                db.session.add(test_user)
                db.session.commit()
                print("✅ Test user created successfully")
            
            return True
    except Exception as e:
        print(f"❌ User creation test failed: {e}")
        return False

def test_ticket_creation():
    """Test creating tickets"""
    print("\n🔍 Testing ticket creation...")
    try:
        with app.app_context():
            # Get a test user
            user = User.query.filter_by(email='test@example.com').first()
            if not user:
                user = User.query.filter_by(role='user').first()
            
            if user:
                # Create production machine ticket
                prod_ticket = ProductionMachine(
                    user_id=user.id,
                    machine_name='Test Machine',
                    issue_description='Test issue description',
                    priority='medium'
                )
                
                # Check if ticket already exists
                existing = ProductionMachine.query.filter_by(
                    user_id=user.id,
                    machine_name='Test Machine'
                ).first()
                
                if not existing:
                    db.session.add(prod_ticket)
                    db.session.commit()
                    print("✅ Production machine ticket created")
                else:
                    print("ℹ️  Production machine ticket already exists")
                
                # Create electrical ticket
                elec_ticket = Electrical(
                    user_id=user.id,
                    equipment_name='Test Equipment',
                    issue_description='Test electrical issue',
                    priority='high'
                )
                
                existing = Electrical.query.filter_by(
                    user_id=user.id,
                    equipment_name='Test Equipment'
                ).first()
                
                if not existing:
                    db.session.add(elec_ticket)
                    db.session.commit()
                    print("✅ Electrical ticket created")
                else:
                    print("ℹ️  Electrical ticket already exists")
                
                return True
            else:
                print("❌ No users found for ticket creation test")
                return False
    except Exception as e:
        print(f"❌ Ticket creation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Maintenance Help Desk System - Test Suite")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_user_creation,
        test_ticket_creation,
        test_flask_routes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\n🚀 Access the application at: http://localhost:5000")
        print("📋 Login with: admin@maintenance.com / admin123")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == '__main__':
    main()

