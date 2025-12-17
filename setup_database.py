#!/usr/bin/env python3
"""
Database setup script for Maintenance Help Desk System
This script creates the database and initial admin user
"""

import pymysql
from app import app, db, User

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='Violin@12',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS maintanence")
            print("✅ Database 'maintanence' created successfully")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def setup_tables():
    """Create all tables"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ All tables created successfully")
            return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_admin_user():
    """Create default admin user"""
    try:
        with app.app_context():
            # Check if admin user already exists
            supermanager = User.query.filter_by(email='supermanager@maintenance.com').first()
            if not supermanager:
                supermanager = User(
                    name='Super Admin',
                    email='supermanager@maintenance.com',
                    employee_id='SADM001',
                    department='IT',
                    unit='Unit-1',
                    role='super_manager'
                )
                supermanager.set_password('supermanager123')
                
                db.session.add(supermanager)
                db.session.commit()
                print("✅ Super Admin user created successfully")
                print("   Email: supermanager@maintenance.com")
                print("   Password: supermanager123")
            else:
                print("ℹ️  Super Admin user already exists")
            return True
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

def create_sample_users():
    """Create sample users for testing"""
    try:
        with app.app_context():
            sample_users = [
                {
                    'name': 'John Doe',
                    'email': 'john.doe@company.com',
                    'unit': 'Production',
                    'role': 'user',
                    'password': 'user123'
                },
                {
                    'name': 'Jane Smith',
                    'email': 'jane.smith@company.com',
                    'unit': 'Electrical',
                    'role': 'user',
                    'password': 'user123'
                },
                {
                    'name': 'Mike Johnson',
                    'email': 'mike.johnson@company.com',
                    'unit': 'Maintenance',
                    'role': 'manager',
                    'password': 'manager123'
                }
            ]
            
            created_count = 0
            for user_data in sample_users:
                existing_user = User.query.filter_by(email=user_data['email']).first()
                if not existing_user:
                    user = User(
                        name=user_data['name'],
                        email=user_data['email'],
                        unit=user_data['unit'],
                        role=user_data['role']
                    )
                    user.set_password(user_data['password'])
                    db.session.add(user)
                    created_count += 1
            
            if created_count > 0:
                db.session.commit()
                print(f"✅ Created {created_count} sample users")
            else:
                print("ℹ️  All sample users already exist")
            return True
    except Exception as e:
        print(f"❌ Error creating sample users: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Maintenance Help Desk Database...")
    print("=" * 50)
    
    # Step 1: Create database
    if not create_database():
        print("❌ Database setup failed")
        return False
    
    # Step 2: Create tables
    if not setup_tables():
        print("❌ Table setup failed")
        return False
    
    # Step 3: Create admin user
    if not create_admin_user():
        print("❌ Admin user setup failed")
        return False
    
    # Step 4: Create sample users
    if not create_sample_users():
        print("❌ Sample users setup failed")
        return False
    
    print("=" * 50)
    print("🎉 Database setup completed successfully!")
    print("\n📋 Login Credentials:")
    print("   Super Admin: supermanager@maintenance.com / supermanager123")
    print("   User:  john.doe@company.com / user123")
    print("   User:  jane.smith@company.com / user123")
    print("   Manager: mike.johnson@company.com / manager123")
    print("\n🚀 You can now run: python app.py")
    
    return True

if __name__ == '__main__':
    main()
