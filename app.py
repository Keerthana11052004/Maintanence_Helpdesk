from flask import Flask, render_template, request, redirect, url_for, flash, session, Blueprint, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import threading
import io
import csv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://keerthana:V!0lin7ec2025@172.31.24.226/maintanence'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = False  # For development
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Email configuration - Outlook SMTP
app.config['MAIL_SERVER'] = 'smtp.office365.com'  # Outlook SMTP
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sapnoreply@violintec.com'
app.config['MAIL_PASSWORD'] = 'VT$ofT@$2025'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'mrwr.login'
login_manager.login_message = 'Please log in to access the Maintenance Help Desk.'
login_manager.login_message_category = 'info'

# Create blueprint with URL prefix
mrwr_bp = Blueprint('mrwr', __name__, url_prefix='/mrwr')

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    employee_id = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'manager', 'super_manager'
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Production Machines Ticket Model
class ProductionMachine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    machine_name = db.Column(db.String(100), nullable=True) # Changed to nullable=True
    vt_machine_number = db.Column(db.String(200), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(50), default='open')  # open, in_progress, closed, pending, hold
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    pending_reason = db.Column(db.Text)
    photo_path = db.Column(db.String(200))
    
    # New fields
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    employee_id = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    unit = db.Column(db.String(50), nullable=False)
    created_date_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Approver fields
    approver_mail = db.Column(db.String(120))
    approved_date_time = db.Column(db.DateTime(timezone=True))
    
    # Resolution fields
    resolved_reason = db.Column(db.Text)
    
    # Close fields
    closed_date_time = db.Column(db.DateTime(timezone=True))
    
    # Grace period fields for reopening
    resolved_date_time = db.Column(db.DateTime(timezone=True))  # When ticket was resolved
    grace_period_end = db.Column(db.DateTime(timezone=True))  # When grace period ends (48 hours after resolution)
    is_in_grace_period = db.Column(db.Boolean, default=False)  # Whether ticket is in grace period
    held_by = db.Column(db.String(120)) # Admin who put the ticket on hold
    hold_reason = db.Column(db.Text) # Reason for holding the ticket
    root_cause = db.Column(db.Text)
    correction = db.Column(db.Text)
    corrective_action = db.Column(db.Text)
    knowledge_based = db.Column(db.Boolean, default=False)
    asset_number = db.Column(db.String(100))

    user = db.relationship('User', backref=db.backref('production_tickets', lazy=True))

# Email Configuration Model
class EmailConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.String(50), nullable=False, unique=True)  # Unit-1, Unit-2, etc.
    email_addresses = db.Column(db.Text, nullable=False)  # Comma-separated email addresses
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def get_email_list(self):
        """Return list of email addresses"""
        if not self.email_addresses:
            return []
        return [email.strip() for email in self.email_addresses.split(',') if email.strip()]

# VT Machine Number Model
class VTMachineNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_number = db.Column(db.String(200), nullable=False)  # e.g., "VT-001 - Production Machine 1 for Unit-1"
    unit = db.Column(db.String(50), nullable=False)  # Unit-1, Unit-2, etc.
    description = db.Column(db.String(200))  # Optional description
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<VTMachineNumber {self.machine_number} - {self.unit}>'

# Electrical Equipment Model
class ElectricalEquipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_name = db.Column(db.String(100), nullable=False)  # e.g., "Fan", "Motor", "Light"
    unit = db.Column(db.String(50), nullable=False)  # Unit-1, Unit-2, etc.
    description = db.Column(db.String(200))  # Optional description
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<ElectricalEquipment {self.equipment_name} - {self.unit}>'

# Electrical Ticket Model
class Electrical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    equipment_name = db.Column(db.String(100), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(50), default='open')  # open, in_progress, closed, pending, hold
    assigned_technician = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    pending_reason = db.Column(db.Text)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    photo_path = db.Column(db.String(200))
    
    # Auto-fetch fields
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    employee_id = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    unit = db.Column(db.String(50), nullable=False)
    created_date_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Approver fields
    approver_mail = db.Column(db.String(120))
    approved_date_time = db.Column(db.DateTime(timezone=True))
    
    # Resolution fields
    resolved_reason = db.Column(db.Text)
    
    # Close fields
    closed_date_time = db.Column(db.DateTime(timezone=True))
    
    # Grace period fields for reopening
    resolved_date_time = db.Column(db.DateTime(timezone=True))  # When ticket was resolved
    grace_period_end = db.Column(db.DateTime(timezone=True))  # When grace period ends (48 hours after resolution)
    is_in_grace_period = db.Column(db.Boolean, default=False)  # Whether ticket is in grace period
    held_by = db.Column(db.String(120)) # Admin who put the ticket on hold
    hold_reason = db.Column(db.Text) # Reason for holding the ticket

    user = db.relationship('User', backref=db.backref('electrical_tickets', lazy=True))

# Ticket History Model
class TicketHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_type = db.Column(db.String(20), nullable=False)  # 'production' or 'electrical'
    ticket_id = db.Column(db.Integer, nullable=False)  # ID of the original ticket
    action = db.Column(db.String(50), nullable=False)  # 'created', 'approved', 'resolved', 'reopened', 'closed'
    performed_by = db.Column(db.String(120), nullable=False)  # Email of user who performed action
    performed_by_name = db.Column(db.String(100), nullable=False)  # Name of user who performed action
    reason = db.Column(db.Text)  # Reason for the action (especially for resolved/reopened)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<TicketHistory {self.ticket_type}#{self.ticket_id} - {self.action} by {self.performed_by_name}>'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def add_ticket_history(ticket_type, ticket_id, action, performed_by_email, performed_by_name, reason=None):
    """Add an entry to ticket history"""
    history = TicketHistory(
        ticket_type=ticket_type,
        ticket_id=ticket_id,
        action=action,
        performed_by=performed_by_email,
        performed_by_name=performed_by_name,
        reason=reason
    )
    db.session.add(history)
    db.session.commit()

def get_ticket_history(ticket_type, ticket_id):
    """Get all history entries for a ticket"""
    return TicketHistory.query.filter_by(
        ticket_type=ticket_type, 
        ticket_id=ticket_id
    ).order_by(TicketHistory.timestamp.desc()).all()

def is_ticket_in_grace_period(ticket):
    """Check if a ticket is still in the 48-hour grace period"""
    if not ticket.is_in_grace_period or not ticket.grace_period_end:
        return False
    grace_period_end = ticket.grace_period_end
    if grace_period_end.tzinfo is None:
        grace_period_end = grace_period_end.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < grace_period_end

def _send_electrical_resolve_notification_email_core(app_context, ticket_data, resolution_type, resolved_by_name):
    with app_context:
        """Core function to send email notification to ticket creator when electrical ticket is resolved"""
        try:
            # Get email configuration for the ticket's unit
            email_config = EmailConfiguration.query.filter_by(unit=ticket_data['unit'], is_active=True).first()
            
            if not email_config:
                print(f"❌ No email configuration found for unit: {ticket_data['unit']}")
                return False
            
            # Create email content
            if resolution_type == 'resolved':
                subject = f"✅ Electrical Ticket #{ticket_data['id']} Resolved - {ticket_data['equipment_name']}"
                body = f"""
Dear {ticket_data['name']},

Your electrical equipment ticket has been successfully resolved!

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- Equipment Name: {ticket_data['equipment_name']}
- Issue: {ticket_data['issue_description']}
- Priority: {ticket_data['priority'].title()}
- Resolved by: {resolved_by_name}
- Resolution: {ticket_data['resolved_reason']}

The ticket is now closed and you have 48 hours to reopen it if needed.

Thank you for using the Maintenance Help Desk.

Best regards,
Maintenance Team
                """
            else:  # not_resolved
                subject = f"⚠️ Electrical Ticket #{ticket_data['id']} Not Resolved - {ticket_data['equipment_name']}"
                body = f"""
Dear {ticket_data['name']},

Your electrical equipment ticket could not be resolved at this time.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- Equipment Name: {ticket_data['equipment_name']}
- Issue: {ticket_data['issue_description']}
- Priority: {ticket_data['priority'].title()}
- Status: Not Resolved
- Reason: {ticket_data['resolved_reason']}

The ticket will be closed by the approver. Please contact the maintenance team for further assistance.

Thank you for using the Maintenance Help Desk.

Best regards,
Maintenance Team
                """
            
            # Send email
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = ticket_data['email']
            
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            print(f"✅ Electrical resolve notification email sent to {ticket_data['email']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send electrical resolve notification email: {e}")
            return False

def send_electrical_resolve_notification_email_async(ticket_data, resolution_type, resolved_by_name):
    """Wrapper to send electrical resolve notification email asynchronously"""
    thread = threading.Thread(target=_send_electrical_resolve_notification_email_core, args=(app.app_context(), ticket_data, resolution_type, resolved_by_name))
    thread.start()
    return True

def _send_resolve_notification_email_core(app_context, ticket_data, resolution_type, resolved_by_name):
    with app_context:
        """Core function to send email notification to ticket creator when ticket is resolved"""
        try:
            # Get email configuration for the ticket's unit
            email_config = EmailConfiguration.query.filter_by(unit=ticket_data['unit'], is_active=True).first()
            
            if not email_config:
                print(f"❌ No email configuration found for unit: {ticket_data['unit']}")
                return False
            
            # Create email content
            if resolution_type == 'resolved':
                subject = f"✅ Ticket #{ticket_data['id']} Resolved - {ticket_data['vt_machine_number']}"
                body = f"""
Dear {ticket_data['name']},

Your production machine ticket has been successfully resolved!

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- VT-machine Details: {ticket_data['vt_machine_number']}
- Asset Number: {ticket_data['asset_number']}
- Issue: {ticket_data['issue_description']}
- Priority: {ticket_data['priority'].title()}
- Resolved by: {resolved_by_name}
- Resolution: {ticket_data['resolved_reason']}
"""
            if ticket_data['knowledge_based']:
                body += f"""
- Root Cause: {ticket_data['root_cause']}
- Correction: {ticket_data['correction']}
- Corrective Action: {ticket_data['corrective_action']}
"""
            body += f"""
The ticket is now closed and you have 48 hours to reopen it if needed.
 
Thank you for using the Maintenance Help Desk.
 
Best regards,
Maintenance Team
"""
            if resolution_type == 'not_resolved':
                subject = f"⚠️ Ticket #{ticket_data['id']} Not Resolved - {ticket_data['vt_machine_number']}"
                body = f"""
Dear {ticket_data['name']},
 
Your production machine ticket could not be resolved at this time.
 
Ticket Details:
- Ticket ID: #{ticket_data['id']}
- VT-machine Details: {ticket_data['vt_machine_number']}
- Asset Number: {ticket_data['asset_number']}
- Issue: {ticket_data['issue_description']}
- Priority: {ticket_data['priority'].title()}
- Status: Not Resolved
- Reason: {ticket_data['resolved_reason']}
 
The ticket will be closed by the approver. Please contact the maintenance team for further assistance.
 
Thank you for using the Maintenance Help Desk.
 
Best regards,
Maintenance Team
                 """
            
            # Send email
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = ticket_data['email']
            
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            print(f"✅ Resolve notification email sent to {ticket_data['email']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send resolve notification email: {e}")
            return False

def send_resolve_notification_email_async(ticket_data, resolution_type, resolved_by_name):
    """Wrapper to send resolve notification email asynchronously"""
    thread = threading.Thread(target=_send_resolve_notification_email_core, args=(app.app_context(), ticket_data, resolution_type, resolved_by_name))
    thread.start()
    return True

def _send_ticket_notification_email_async(app_context, ticket_data):
    with app_context:
        """Send email notification to configured recipients based on unit when a new ticket is created (asynchronous)"""
        try:
            # Get email configuration for the ticket's unit
            email_config = EmailConfiguration.query.filter_by(unit=ticket_data['unit'], is_active=True).first()
            
            if not email_config:
                print(f"No email configuration found for unit: {ticket_data['unit']}")
                # Fallback to all manager users if no unit configuration exists
                manager_users = User.query.filter(User.role.in_(['manager', 'super_manager'])).all()
                if not manager_users:
                    print("No manager users found to send notification")
                    return False
                recipient_emails = [manager.email for manager in manager_users]
            else:
                recipient_emails = email_config.get_email_list()
                if not recipient_emails:
                    print(f"No email addresses configured for unit: {ticket_data['unit']}")
                    return False
            
            # Create email content
            subject = f"New Production Machine Ticket #{ticket_data['id']} - {ticket_data['vt_machine_number']}"
            
            # HTML email body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        🚨 New Production Machine Ticket
                    </h2>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #e74c3c; margin-top: 0;">Ticket Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; width: 30%;">Ticket ID:</td>
                                <td style="padding: 8px;">#{ticket_data['id']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">VT-machine Details:</td>
                                <td style="padding: 8px;">{ticket_data['vt_machine_number']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Asset Number:</td>
                                <td style="padding: 8px;">{ticket_data['asset_number']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Priority:</td>
                                <td style="padding: 8px;">
                                    <span style="background-color: {'#e74c3c' if ticket_data['priority'] == 'high' else '#f39c12' if ticket_data['priority'] == 'medium' else '#27ae60'}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">
                                        {ticket_data['priority'].title()}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Status:</td>
                                <td style="padding: 8px;">
                                    <span style="background-color: #27ae60; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">
                                        {ticket_data['status'].title()}
                                    </span>
                                </td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Created Date:</td>
                                <td style="padding: 8px;">{ticket_data['created_date_time']}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Requester Information</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; width: 30%;">Name:</td>
                                <td style="padding: 8px;">{ticket_data['name']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Email:</td>
                                <td style="padding: 8px;">{ticket_data['email']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Employee ID:</td>
                                <td style="padding: 8px;">{ticket_data.get('employee_id', 'N/A')}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Department:</td>
                                <td style="padding: 8px;">{ticket_data.get('department', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Unit:</td>
                                <td style="padding: 8px;">{ticket_data['unit']}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Issue Description</h3>
                        <p style="background-color: white; padding: 10px; border-radius: 3px; border-left: 4px solid #3498db;">
                            {ticket_data['issue_description']}
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://127.0.0.1:5002/mrwr/manager/approve_ticket_from_email/{ticket_data['id']}"
                           style="background-color: #27ae60; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-right: 10px;">
                            ✅ Approve Ticket
                        </a>
                        <a href="http://127.0.0.1:5002/mrwr/manager/production"
                           style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            View Ticket in Admin Panel
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
                    <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                        This is an automated notification from the Maintenance Help Desk System.<br>
                        Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_body = f"""
New Production Machine Ticket #{ticket_data['id']}

Ticket Details:
- VT-machine Details: {ticket_data['vt_machine_number']}
- Asset Number: {ticket_data['asset_number']}
- Priority: {ticket_data['priority'].title()}
- Status: {ticket_data['status'].title()}
- Created Date: {ticket_data['created_date_time']}

Requester Information:
- Name: {ticket_data['name']}
- Email: {ticket_data['email']}
- Employee ID: {ticket_data.get('employee_id', 'N/A')}
- Department: {ticket_data.get('department', 'N/A')}
- Unit: {ticket_data['unit']}

Issue Description:
{ticket_data['issue_description']}

View ticket: http://127.0.0.1:5002/mrwr/manager/production

This is an automated notification from the Maintenance Help Desk System.
        """
        
            # Join all recipient emails into a single string for the 'To' field
            to_emails = ", ".join(recipient_emails)
            print(f"📧 DEBUG: Sending email to combined recipients: {to_emails}")

            # Establish SMTP connection once
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

                try:
                    # Create message
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From'] = app.config['MAIL_USERNAME']
                    msg['To'] = to_emails  # Send to all recipients at once
                    
                    # Add both plain text and HTML versions
                    text_part = MIMEText(text_body, 'plain')
                    html_part = MIMEText(html_body, 'html')
                    
                    msg.attach(text_part)
                    msg.attach(html_part)
                    
                    # Send email
                    server.send_message(msg)
                    
                    print(f"✅ DEBUG: Email sent successfully to {to_emails}")
                    return True
                    
                except Exception as e:
                    print(f"❌ DEBUG: Failed to send email to {to_emails}: {e}")
                    if "BadCredentials" in str(e):
                        print("💡 Authentication failed - check email credentials")
                    elif "Connection refused" in str(e):
                        print("💡 Connection failed - check internet connection")
                    elif "550" in str(e):
                        print("💡 Email address might be invalid or rejected by server")
                    elif "553" in str(e):
                        print("💡 Email address format might be invalid")
                    else:
                        print(f"💡 Other error: {type(e).__name__}")
                    return False
                
        except Exception as e:
            print(f"Error sending email notifications: {e}")
            return False

def send_ticket_notification_email(ticket_data):
    """Wrapper to send email notification asynchronously"""
    # Pass app.app_context() to the thread
    thread = threading.Thread(target=_send_ticket_notification_email_async, args=(app.app_context(), ticket_data))
    thread.start()
    return True # Return immediately, email will be sent in background

def _send_electrical_ticket_notification_email_async(app_context, ticket_data):
    with app_context:
        """Send email notification to configured recipients based on unit when a new electrical ticket is created (asynchronous)"""
        try:
            # Get email configuration for the ticket's unit
            email_config = EmailConfiguration.query.filter_by(unit=ticket_data['unit'], is_active=True).first()
            
            if not email_config:
                print(f"No email configuration found for unit: {ticket_data['unit']}")
                # Fallback to all manager users if no unit configuration exists
                manager_users = User.query.filter(User.role.in_(['manager', 'super_manager'])).all()
                if not manager_users:
                    print("No manager users found to send notification")
                    return False
                recipient_emails = [manager.email for manager in manager_users]
            else:
                recipient_emails = email_config.get_email_list()
                if not recipient_emails:
                    print(f"No email addresses configured for unit: {ticket_data['unit']}")
                    return False
            
            # Create email content
            subject = f"New Electrical Ticket #{ticket_data['id']} - {ticket_data['equipment_name']}"
            
            # HTML email body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #f39c12; padding-bottom: 10px;">
                        ⚡ New Electrical Ticket
                    </h2>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #e74c3c; margin-top: 0;">Ticket Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; width: 30%;">Ticket ID:</td>
                                <td style="padding: 8px;">#{ticket_data['id']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Equipment Name:</td>
                                <td style="padding: 8px;">{ticket_data['equipment_name']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Priority:</td>
                                <td style="padding: 8px;">
                                    <span style="background-color: {'#e74c3c' if ticket_data['priority'] == 'high' else '#f39c12' if ticket_data['priority'] == 'medium' else '#27ae60'}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">
                                        {ticket_data['priority'].title()}
                                    </span>
                                </td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Status:</td>
                                <td style="padding: 8px;">
                                    <span style="background-color: #27ae60; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">
                                        {ticket_data['status'].title()}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Created Date:</td>
                                <td style="padding: 8px;">{ticket_data['created_date_time']}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Requester Information</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; width: 30%;">Name:</td>
                                <td style="padding: 8px;">{ticket_data['name']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Email:</td>
                                <td style="padding: 8px;">{ticket_data['email']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Employee ID:</td>
                                <td style="padding: 8px;">{ticket_data.get('employee_id', 'N/A')}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Department:</td>
                                <td style="padding: 8px;">{ticket_data.get('department', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Unit:</td>
                                <td style="padding: 8px;">{ticket_data['unit']}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Issue Description</h3>
                        <p style="background-color: white; padding: 10px; border-radius: 3px; border-left: 4px solid #f39c12;">
                            {ticket_data['issue_description']}
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://127.0.0.1:5002/mrwr/manager/approve_ticket_from_email/electrical/{ticket_data['id']}"
                           style="background-color: #27ae60; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-right: 10px;">
                            ✅ Approve Ticket
                        </a>
                        <a href="http://127.0.0.1:5002/mrwr/manager/electrical"
                           style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            View Ticket in Admin Panel
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
                    <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                        This is an automated notification from the Maintenance Help Desk System.<br>
                        Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_body = f"""
New Electrical Ticket #{ticket_data['id']}

Ticket Details:
- Equipment Name: {ticket_data['equipment_name']}
- Priority: {ticket_data['priority'].title()}
- Status: {ticket_data['status'].title()}
- Created Date: {ticket_data['created_date_time']}

Requester Information:
- Name: {ticket_data['name']}
- Email: {ticket_data['email']}
- Employee ID: {ticket_data.get('employee_id', 'N/A')}
- Department: {ticket_data.get('department', 'N/A')}
- Unit: {ticket_data['unit']}

Issue Description:
{ticket_data['issue_description']}

View ticket: http://127.0.0.1:5002/mrwr/manager/electrical

This is an automated notification from the Maintenance Help Desk System.
        """
        
            # Join all recipient emails into a single string for the 'To' field
            to_emails = ", ".join(recipient_emails)
            print(f"📧 DEBUG: Sending electrical email to combined recipients: {to_emails}")

            # Establish SMTP connection once
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

                try:
                    # Create message
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From'] = app.config['MAIL_USERNAME']
                    msg['To'] = to_emails  # Send to all recipients at once
                    
                    # Attach both HTML and plain text versions
                    part1 = MIMEText(text_body, 'plain')
                    part2 = MIMEText(html_body, 'html')
                    
                    msg.attach(part1)
                    msg.attach(part2)
                    
                    # Send email
                    server.send_message(msg)
                    
                    print(f"✅ DEBUG: Electrical email sent successfully to {to_emails}")
                    return True
                    
                except Exception as e:
                    print(f"❌ DEBUG: Failed to send electrical email to {to_emails}: {e}")
                    if "BadCredentials" in str(e):
                        print("💡 Authentication failed - check email credentials")
                    elif "Connection refused" in str(e):
                        print("💡 Connection failed - check internet connection")
                    elif "550" in str(e):
                        print("💡 Email address might be invalid or rejected by server")
                    elif "553" in str(e):
                        print("💡 Email address format might be invalid")
                    else:
                        print(f"💡 Other error: {e}")
                    return False
                
        except Exception as e:
            print(f"Error sending electrical ticket email notifications: {e}")
            return False

def send_electrical_ticket_notification_email(ticket_data):
    """Wrapper to send electrical email notification asynchronously"""
    # Pass app.app_context() to the thread
    thread = threading.Thread(target=_send_electrical_ticket_notification_email_async, args=(app.app_context(), ticket_data))
    thread.start()
    return True # Return immediately, email will be sent in background

def _send_reopen_notification_email_async(app_context, ticket_data, ticket_type):
    with app_context:
        """Send email notification to configured recipients based on unit when a ticket is reopened (asynchronous)"""
        try:
            # Get email configuration for the ticket's unit
            email_config = EmailConfiguration.query.filter_by(unit=ticket_data['unit'], is_active=True).first()
            
            if not email_config:
                print(f"No email configuration found for unit: {ticket_data['unit']}")
                # Fallback to all manager users if no unit configuration exists
                manager_users = User.query.filter(User.role.in_(['manager', 'super_manager'])).all()
                if not manager_users:
                    print("No manager users found to send notification")
                    return False
                recipient_emails = [manager.email for manager in manager_users]
            else:
                recipient_emails = email_config.get_email_list()
                if not recipient_emails:
                    print(f"No email addresses configured for unit: {ticket_data['unit']}")
                    return False
            
            # Determine subject and specific details based on ticket type
            if ticket_type == 'production':
                subject = f"🔄 Ticket #{ticket_data['id']} Reopened - {ticket_data['vt_machine_number']}"
                item_name_label = "VT-machine Details"
                item_name = ticket_data['vt_machine_number']
            elif ticket_type == 'electrical':
                subject = f"🔄 Electrical Ticket #{ticket_data['id']} Reopened - {ticket_data['equipment_name']}"
                item_name_label = "Equipment Name"
                item_name = ticket_data['equipment_name']
            else:
                subject = f"🔄 Ticket #{ticket_data['id']} Reopened"
                item_name_label = "Item Name"
                item_name = "N/A"

            # HTML email body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #f39c12; padding-bottom: 10px;">
                        🔄 Ticket Reopened
                    </h2>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #e74c3c; margin-top: 0;">Ticket Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; width: 30%;">Ticket ID:</td>
                                <td style="padding: 8px;">#{ticket_data['id']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">{item_name_label}:</td>
                                <td style="padding: 8px;">{item_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Asset Number:</td>
                                <td style="padding: 8px;">{ticket_data['asset_number']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Status:</td>
                                <td style="padding: 8px;">
                                    <span style="background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">
                                        Reopened
                                    </span>
                                </td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Reopened By:</td>
                                <td style="padding: 8px;">{ticket_data['name']} ({ticket_data['email']})</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Reopen Reason:</td>
                                <td style="padding: 8px;">{ticket_data['reopen_reason']}</td>
                            </tr>
                            <tr style="background-color: #ecf0f1;">
                                <td style="padding: 8px; font-weight: bold;">Unit:</td>
                                <td style="padding: 8px;">{ticket_data['unit']}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://127.0.0.1:5002/mrwr/manager/{ticket_type}"
                           style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                            View Ticket in Admin Panel
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
                    <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                        This is an automated notification from the Maintenance Help Desk System.<br>
                        Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_body = f"""
Ticket #{ticket_data['id']} Reopened

Ticket Details:
- {item_name_label}: {item_name}
- Asset Number: {ticket_data['asset_number']}
- Status: Reopened
- Reopened By: {ticket_data['name']} ({ticket_data['email']})
- Reopen Reason: {ticket_data['reopen_reason']}
- Unit: {ticket_data['unit']}

View ticket: http://127.0.0.1:5002/mrwr/manager/{ticket_type}

This is an automated notification from the Maintenance Help Desk System.
        """
        
            # Join all recipient emails into a single string for the 'To' field
            to_emails = ", ".join(recipient_emails)
            print(f"📧 DEBUG: Sending reopen email to combined recipients: {to_emails}")

            # Establish SMTP connection once
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

                try:
                    # Create message
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From'] = app.config['MAIL_USERNAME']
                    msg['To'] = to_emails  # Send to all recipients at once
                    
                    # Add both plain text and HTML versions
                    text_part = MIMEText(text_body, 'plain')
                    html_part = MIMEText(html_body, 'html')
                    
                    msg.attach(text_part)
                    msg.attach(html_part)
                    
                    # Send email
                    server.send_message(msg)
                    
                    print(f"✅ DEBUG: Reopen email sent successfully to {to_emails}")
                    return True
                    
                except Exception as e:
                    print(f"❌ DEBUG: Failed to send reopen email to {to_emails}: {e}")
                    if "BadCredentials" in str(e):
                        print("💡 Authentication failed - check email credentials")
                    elif "Connection refused" in str(e):
                        print("💡 Connection failed - check internet connection")
                    elif "550" in str(e):
                        print("💡 Email address might be invalid or rejected by server")
                    elif "553" in str(e):
                        print("💡 Email address format might be invalid")
                    else:
                        print(f"💡 Other error: {type(e).__name__}")
                    return False
                
        except Exception as e:
            print(f"Error sending reopen email notifications: {e}")
            return False

def send_reopen_notification_email_async(ticket_data, ticket_type):
    """Wrapper to send reopen notification email asynchronously"""
    thread = threading.Thread(target=_send_reopen_notification_email_async, args=(app.app_context(), ticket_data, ticket_type))
    thread.start()
    return True

def _send_reassign_notification_email_core(app_context, recipient_email, ticket_data, ticket_type):
    with app_context:
        """Core function to send email notification to the new manager when a ticket is reassigned"""
        try:
            if ticket_type == 'production':
                subject = f"Ticket #{ticket_data['id']} Reassigned - {ticket_data['vt_machine_number']}"
                body = f"""
Dear Admin,

A production machine ticket has been reassigned to you.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- VT-machine Details: {ticket_data['vt_machine_number']}
- Assigned By: {ticket_data['assigned_by']}

Please review the ticket in the manager panel.

Best regards,
Maintenance Team
                """
            else: # electrical
                subject = f"Electrical Ticket #{ticket_data['id']} Reassigned - {ticket_data['equipment_name']}"
                body = f"""
Dear Admin,

An electrical equipment ticket has been reassigned to you.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- Equipment Name: {ticket_data['equipment_name']}
- Assigned By: {ticket_data['assigned_by']}

Please review the ticket in the manager panel.

Best regards,
Maintenance Team
                """

            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = recipient_email

            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)

            print(f"✅ Reassign notification email sent to {recipient_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send reassign notification email to {recipient_email}: {e}")
            return False

def send_reassign_notification_email_async(recipient_email, ticket_data, ticket_type):
    """Wrapper to send reassign notification email asynchronously"""
    thread = threading.Thread(target=_send_reassign_notification_email_core, args=(app.app_context(), recipient_email, ticket_data, ticket_type))
    thread.start()
    return True

def _send_pending_notification_email_core(app_context, ticket_data, ticket_type):
    with app_context:
        """Core function to send email notification to ticket creator when ticket is marked as pending"""
        try:
            if ticket_type == 'production':
                subject = f"⏳ Your Production Ticket #{ticket_data['id']} is Pending"
                body = f"""
Dear {ticket_data['name']},

Your production machine ticket is currently pending.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- VT-machine Details: {ticket_data['vt_machine_number']}
- Issue: {ticket_data['issue_description']}
- Reason for Pending: {ticket_data['pending_reason']}

Our team will review it shortly. Thank you for your patience.

Best regards,
Maintenance Team
                """
            else:
                subject = f"⏳ Your Electrical Ticket #{ticket_data['id']} is Pending"
                body = f"""
Dear {ticket_data['name']},

Your electrical equipment ticket is currently pending.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- Equipment Name: {ticket_data['equipment_name']}
- Issue: {ticket_data['issue_description']}
- Reason for Pending: {ticket_data['pending_reason']}

Our team will review it shortly. Thank you for your patience.

Best regards,
Maintenance Team
                """

            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = ticket_data['email']

            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)

            print(f"✅ Pending notification email sent to {ticket_data['email']}")
            return True

        except Exception as e:
            print(f"❌ Failed to send pending notification email: {e}")
            return False

def send_pending_notification_email_async(ticket_data, ticket_type):
    """Wrapper to send pending notification email asynchronously"""
    thread = threading.Thread(target=_send_pending_notification_email_core, args=(app.app_context(), ticket_data, ticket_type))
    thread.start()
    return True

def _send_hold_notification_email_core(app_context, ticket_data, ticket_type):
    with app_context:
        """Core function to send email notification to supermanager when a ticket is put on hold"""
        try:
            supermanager = User.query.filter_by(role='super_manager').first()
            if not supermanager:
                print("❌ No supermanager found to send hold notification email.")
                return False

            if ticket_type == 'production':
                subject = f"⏸️ Production Ticket #{ticket_data['id']} on Hold"
                body = f"""
Dear Super Admin,

A production machine ticket has been placed on hold.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- VT-machine Details: {ticket_data['vt_machine_number']}
- Held By: {ticket_data['held_by']}
- Reason for Hold: {ticket_data['hold_reason']}

Please review the ticket in the manager panel.

Best regards,
Maintenance Team
                """
            else: # electrical
                subject = f"⏸️ Electrical Ticket #{ticket_data['id']} on Hold"
                body = f"""
Dear Super Admin,

An electrical equipment ticket has been placed on hold.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- Equipment Name: {ticket_data['equipment_name']}
- Held By: {ticket_data['held_by']}
- Reason for Hold: {ticket_data['hold_reason']}

Please review the ticket in the manager panel.

Best regards,
Maintenance Team
                """

            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = supermanager.email

            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)

            print(f"✅ Hold notification email sent to supermanager {supermanager.email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send hold notification email: {e}")
            return False

def send_hold_notification_email_async(supermanager_email, ticket_data, ticket_type):
    """Wrapper to send hold notification email asynchronously"""
    thread = threading.Thread(target=_send_hold_notification_email_core, args=(app.app_context(), ticket_data, ticket_type))
    thread.start()
    return True

def _send_resume_notification_email_core(app_context, ticket_data, ticket_type):
    with app_context:
        """Core function to send email notification to supermanager when a ticket is resumed"""
        try:
            supermanager = User.query.filter_by(role='super_manager').first()
            if not supermanager:
                print("❌ No supermanager found to send resume notification email.")
                return False

            if ticket_type == 'production':
                subject = f"▶️ Production Ticket #{ticket_data['id']} Resumed"
                body = f"""
Dear Super Admin,

A production machine ticket has been resumed from hold status.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- VT-machine Details: {ticket_data['vt_machine_number']}
- Resumed By: {ticket_data['resumed_by']}

The ticket is now in progress.

Best regards,
Maintenance Team
                """
            else: # electrical
                subject = f"▶️ Electrical Ticket #{ticket_data['id']} Resumed"
                body = f"""
Dear Super Admin,

An electrical equipment ticket has been resumed from hold status.

Ticket Details:
- Ticket ID: #{ticket_data['id']}
- Equipment Name: {ticket_data['equipment_name']}
- Resumed By: {ticket_data['resumed_by']}

The ticket is now in progress.

Best regards,
Maintenance Team
                """

            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = supermanager.email

            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)

            print(f"✅ Resume notification email sent to supermanager {supermanager.email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send resume notification email: {e}")
            return False

def send_resume_notification_email_async(ticket_data, ticket_type):
    """Wrapper to send resume notification email asynchronously"""
    thread = threading.Thread(target=_send_resume_notification_email_core, args=(app.app_context(), ticket_data, ticket_type))
    thread.start()
    return True

# Routes
@app.route('/')
def index():
    return redirect(url_for('mrwr.login'))

@mrwr_bp.route('/')
def mrwr_index():
    if current_user.is_authenticated:
        return redirect(url_for('mrwr.dashboard'))
    return redirect(url_for('mrwr.login'))

@mrwr_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # If already authenticated, log out to force re-login or allow access to login page
        logout_user()
        flash('You have been logged out to access the login page.', 'info')
        return redirect(url_for('mrwr.login')) # Redirect back to login after logout
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            print(f"✅ User '{email}' logged in successfully.")
            return redirect(url_for('mrwr.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            print(f"❌ Failed login attempt for user '{email}'.")
            
    return render_template('login.html')

@mrwr_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('mrwr.login'))

@mrwr_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role in ['manager', 'super_manager']:
        # Manager/S.Manager dashboard
        total_production = ProductionMachine.query.count()
        total_electrical = Electrical.query.count()
        open_production = ProductionMachine.query.filter_by(status='open').count()
        open_electrical = Electrical.query.filter_by(status='open').count()
        in_progress_production = ProductionMachine.query.filter_by(status='in_progress').count()
        in_progress_electrical = Electrical.query.filter_by(status='in_progress').count()
        
        return render_template('admin_dashboard.html',
                             total_production=total_production,
                             total_electrical=total_electrical,
                             open_production=open_production,
                             open_electrical=open_electrical,
                             in_progress_production=in_progress_production,
                             in_progress_electrical=in_progress_electrical,
                             current_user=current_user)
    else:
        # User dashboard
        user_production = ProductionMachine.query.filter_by(user_id=current_user.id).count()
        user_electrical = Electrical.query.filter_by(user_id=current_user.id).count()
        open_user_production = ProductionMachine.query.filter_by(user_id=current_user.id, status='open').count()
        open_user_electrical = Electrical.query.filter_by(user_id=current_user.id, status='open').count()
        
        return render_template('user_dashboard.html',
                             user_production=user_production,
                             user_electrical=user_electrical,
                             open_user_production=open_user_production,
                             open_user_electrical=open_user_electrical)

@mrwr_bp.route('/raise_ticket/production', methods=['GET', 'POST'])
@login_required
def raise_production_ticket():
    print(f"Production Ticket Route - Method: {request.method}")
    print(f"Production Ticket Route - User authenticated: {current_user.is_authenticated}")
    print(f"Production Ticket Route - Current user: {current_user}")
    
    if request.method == 'POST':
        try:
            vt_machine_number_full = request.form['vt_machine_number']
            # Extract just the machine number for the database if needed, or store the full string
            # For now, we'll store the full string as the column size has been increased
            vt_machine_number = vt_machine_number_full
            issue_description = request.form['issue_description']
            priority = request.form['priority']
            name = request.form['name']
            email = request.form['email']
            employee_id = request.form.get('employee_id', '')
            department = request.form.get('department', '')
            unit = request.form['unit']
            created_date_time = request.form['created_date_time']
            asset_number = request.form.get('asset_number', '')

            # Check if user is authenticated
            if not current_user.is_authenticated:
                flash('Please log in to submit a ticket.', 'error')
                # Filter VT machines based on user's unit
                user_unit = current_user.unit if current_user.is_authenticated else None
                if user_unit:
                    vt_machines = VTMachineNumber.query.filter_by(unit=user_unit, is_active=True).order_by(VTMachineNumber.machine_number).all()
                else:
                    vt_machines = VTMachineNumber.query.filter_by(is_active=True).order_by(VTMachineNumber.unit, VTMachineNumber.machine_number).all()
                return render_template('raise_production_ticket.html', vt_machines=vt_machines)
            
            print(f"Production Ticket - Received data: vt_machine_number={vt_machine_number}, asset_number={asset_number}, issue_description={issue_description}, priority={priority}, name={name}, email={email}, employee_id={employee_id}, department={department}, unit={unit}, created_date_time={created_date_time}, user_id={current_user.id}")
            
            # Convert datetime string to datetime object
            from datetime import datetime
            created_dt = datetime.fromisoformat(created_date_time.replace('T', ' '))
        
            ticket = ProductionMachine(
                user_id=current_user.id,
                machine_name="N/A", # Set a default value or remove the column if not needed
                vt_machine_number=vt_machine_number,
                asset_number=asset_number,
                issue_description=issue_description,
                priority=priority,
                name=name,
                email=email,
                employee_id=employee_id,
                department=department,
                unit=unit,
                created_date_time=created_dt
            )
            
            db.session.add(ticket)
            db.session.commit()
            print(f"Production Ticket - Ticket created successfully with ID {ticket.id}")
            
            # Add to history
            add_ticket_history('production', ticket.id, 'created', current_user.email, current_user.name)
            
            # Send email notification to all managers
            ticket_data = {
                'id': ticket.id,
                'machine_name': "N/A", # Set a default value or remove from email template
                'vt_machine_number': vt_machine_number_full,
                'asset_number': asset_number,
                'issue_description': issue_description,
                'priority': priority,
                'status': 'open',
                'name': name,
                'email': email,
                'employee_id': employee_id,
                'department': department,
                'unit': unit,
                'created_date_time': created_dt.strftime('%Y-%m-%d %H:%M')
            }
            
            # Send email notification (non-blocking)
            try:
                print("Attempting to send email notifications to managers...")
                email_result = send_ticket_notification_email(ticket_data)
                if email_result:
                    print("✅ Email notifications sent successfully to all managers (in background)")
                else:
                    print("❌ Email notifications failed - check SMTP configuration")
            except Exception as email_error:
                print(f"❌ Failed to send email notifications: {email_error}")
                print("💡 Tip: Check if Gmail App Password is configured correctly")
                # Don't fail the ticket creation if email fails
            
            flash('Production machine ticket raised successfully!', 'success')
            return redirect(url_for('mrwr.my_production_tickets'))
    
        except Exception as e:
            db.session.rollback()
            print(f"Production Ticket - Error: {e}")
            flash('Error creating ticket. Please try again.', 'error')
            # Filter VT machines based on user's unit
            user_unit = current_user.unit if current_user.is_authenticated else None
            if user_unit:
                vt_machines = VTMachineNumber.query.filter_by(unit=user_unit, is_active=True).order_by(VTMachineNumber.machine_number).all()
            else:
                vt_machines = VTMachineNumber.query.filter_by(is_active=True).order_by(VTMachineNumber.unit, VTMachineNumber.machine_number).all()
            return render_template('raise_production_ticket.html', vt_machines=vt_machines)
    
    # GET request - show the form
    # Filter VT machines based on user's unit
    user_unit = current_user.unit if current_user.is_authenticated else None
    if user_unit:
        vt_machines = VTMachineNumber.query.filter_by(unit=user_unit, is_active=True).order_by(VTMachineNumber.machine_number).all()
    else:
        vt_machines = VTMachineNumber.query.filter_by(is_active=True).order_by(VTMachineNumber.unit, VTMachineNumber.machine_number).all()
    
    return render_template('raise_production_ticket.html', vt_machines=vt_machines)

@mrwr_bp.route('/raise_ticket/electrical', methods=['GET', 'POST'])
@login_required
def raise_electrical_ticket():
    if request.method == 'POST':
        equipment_name = request.form['equipment_name']
        issue_description = request.form['issue_description']
        priority = request.form['priority']
        
        # Auto-fetch user data
        name = current_user.name
        email = current_user.email
        employee_id = current_user.employee_id
        department = current_user.department
        unit = current_user.unit
        created_dt = datetime.now(timezone.utc)
        
        ticket = Electrical(
            user_id=current_user.id,
            equipment_name=equipment_name,
            issue_description=issue_description,
            priority=priority,
            name=name,
            email=email,
            employee_id=employee_id,
            department=department,
            unit=unit,
            created_date_time=created_dt
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Add to history
        add_ticket_history('electrical', ticket.id, 'created', current_user.email, current_user.name)
        
        # Send email notification
        try:
            ticket_data = {
                'id': ticket.id,
                'equipment_name': equipment_name,
                'issue_description': issue_description,
                'priority': priority,
                'status': 'open',
                'name': name,
                'email': email,
                'employee_id': employee_id,
                'department': department,
                'unit': unit,
                'created_date_time': created_dt.strftime('%Y-%m-%d %H:%M')
            }
            
            email_sent = send_electrical_ticket_notification_email(ticket_data)
            if email_sent:
                print(f"✅ Electrical ticket notification email sent for ticket #{ticket.id}")
            else:
                print(f"⚠️ Failed to send electrical ticket notification email for ticket #{ticket.id}")
                # Don't fail the ticket creation if email fails
            
        except Exception as e:
            print(f"Error sending electrical ticket notification email: {e}")
            # Don't fail the ticket creation if email fails
        
        flash('Electrical ticket raised successfully!', 'success')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    # Fetch electrical equipment filtered by current user's unit
    electrical_equipment = ElectricalEquipment.query.filter_by(
        unit=current_user.unit,
        is_active=True
    ).order_by(ElectricalEquipment.equipment_name).all()
    
    return render_template('raise_electrical_ticket.html', electrical_equipment=electrical_equipment)

@mrwr_bp.route('/my_tickets/production')
@login_required
def my_production_tickets():
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Number of items per page

    query = ProductionMachine.query.filter_by(user_id=current_user.id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    paginated_tickets = query.order_by(ProductionMachine.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tickets = paginated_tickets.items

    # Get ticket history for each ticket
    tickets_with_history = []
    for ticket in tickets:
        history = get_ticket_history('production', ticket.id)
        tickets_with_history.append((ticket, history))
    
    return render_template('my_production_tickets.html',
                           tickets_with_history=tickets_with_history,
                           current_filter=status_filter,
                           pagination=paginated_tickets)

@mrwr_bp.route('/my_tickets/electrical')
@login_required
def my_electrical_tickets():
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Number of items per page

    query = Electrical.query.filter_by(user_id=current_user.id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    paginated_tickets = query.order_by(Electrical.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tickets = paginated_tickets.items
    
    # Get ticket history for each ticket
    tickets_with_history = []
    for ticket in tickets:
        history = get_ticket_history('electrical', ticket.id)
        tickets_with_history.append((ticket, history))
    
    return render_template('my_electrical_tickets.html',
                           tickets_with_history=tickets_with_history,
                           current_filter=status_filter,
                           pagination=paginated_tickets)

@mrwr_bp.route('/edit_ticket/production/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def edit_production_ticket(ticket_id):
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    # Check if user owns the ticket and it's not assigned
    if ticket.user_id != current_user.id or ticket.status != 'open':
        flash('You can only edit your own unassigned tickets', 'error')
        return redirect(url_for('mrwr.my_production_tickets'))
    
    if request.method == 'POST':
        # Removed machine_name from form processing
        ticket.issue_description = request.form['issue_description']
        ticket.priority = request.form['priority']
        ticket.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash('Ticket updated successfully!', 'success')
        return redirect(url_for('mrwr.my_production_tickets'))
    
    return render_template('edit_production_ticket.html', ticket=ticket)

@mrwr_bp.route('/edit_ticket/electrical/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def edit_electrical_ticket(ticket_id):
    ticket = Electrical.query.get_or_404(ticket_id)
    
    # Check if user owns the ticket and it's not assigned
    if ticket.user_id != current_user.id or ticket.status != 'open':
        flash('You can only edit your own unassigned tickets', 'error')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    if request.method == 'POST':
        ticket.equipment_name = request.form['equipment_name']
        ticket.issue_description = request.form['issue_description']
        ticket.priority = request.form['priority']
        ticket.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash('Ticket updated successfully!', 'success')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    return render_template('edit_electrical_ticket.html', ticket=ticket)

# Admin Routes
@mrwr_bp.route('/manager/production')
@login_required
def manager_production():
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    status_filter = request.args.get('status', 'all')
    asset_number_filter = request.args.get('asset_number', '').strip()
    vt_machine_number_filter = request.args.get('vt_machine_number_filter', 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Number of items per page

    query = ProductionMachine.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if asset_number_filter:
        query = query.filter(ProductionMachine.asset_number.ilike(f'%{asset_number_filter}%'))
    if vt_machine_number_filter != 'all':
        query = query.filter(ProductionMachine.vt_machine_number.ilike(f'%{vt_machine_number_filter}%'))
    
    paginated_tickets = query.order_by(ProductionMachine.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tickets = paginated_tickets.items
    
    # Get ticket history for each ticket and update grace period status
    tickets_with_history = []
    for ticket in tickets:
        # Update grace period status if needed
        if ticket.is_in_grace_period and ticket.grace_period_end:
            if ticket.grace_period_end.tzinfo is None:
                grace_period_end = ticket.grace_period_end.replace(tzinfo=timezone.utc)
            else:
                grace_period_end = ticket.grace_period_end

            if datetime.now(timezone.utc) >= grace_period_end:
                ticket.is_in_grace_period = False
                db.session.commit()
        
        history = get_ticket_history('production', ticket.id)
        tickets_with_history.append((ticket, history))
    
    # Fetch managers for the reassign dropdown, filtered by the ticket's unit
    # This needs to be done for each ticket to ensure unit-specific managers
    
    # For the overall page, we still need a list of all managers for the filter dropdowns if any
    all_managers = User.query.filter(User.role.in_(['manager', 'super_manager'])).order_by(User.name).all()

    tickets_with_history_and_unit_managers = []
    for ticket, history in tickets_with_history:
        unit_managers = User.query.filter(
            User.role.in_(['manager', 'super_manager']),
            User.unit == ticket.unit
        ).order_by(User.name).all()
        tickets_with_history_and_unit_managers.append((ticket, history, unit_managers))

    vt_machines = VTMachineNumber.query.filter_by(is_active=True).order_by(VTMachineNumber.unit, VTMachineNumber.machine_number).all()
    return render_template('manager_production.html',
                           tickets_with_history=tickets_with_history_and_unit_managers,
                           current_filter=status_filter,
                           asset_number_filter=asset_number_filter,
                           vt_machine_number_filter=vt_machine_number_filter,
                           managers=all_managers, # Pass all managers for general use if needed
                           pagination=paginated_tickets,
                           vt_machines=vt_machines)

@mrwr_bp.route('/manager/electrical')
@login_required
def manager_electrical():
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Number of items per page

    query = Electrical.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    paginated_tickets = query.order_by(Electrical.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tickets = paginated_tickets.items
    
    # Get ticket history for each ticket and update grace period status
    tickets_with_history_and_unit_managers = []
    for ticket in tickets:
        # Update grace period status if needed
        if ticket.is_in_grace_period and ticket.grace_period_end:
            if ticket.grace_period_end.tzinfo is None:
                grace_period_end = ticket.grace_period_end.replace(tzinfo=timezone.utc)
            else:
                grace_period_end = ticket.grace_period_end

            if datetime.now(timezone.utc) >= grace_period_end:
                ticket.is_in_grace_period = False
                db.session.commit()
        
        history = get_ticket_history('electrical', ticket.id)
        unit_managers = User.query.filter(
            User.role.in_(['manager', 'super_manager']),
            User.unit == ticket.unit
        ).order_by(User.name).all()
        tickets_with_history_and_unit_managers.append((ticket, history, unit_managers))
    
    all_managers = User.query.filter(User.role.in_(['manager', 'super_manager'])).order_by(User.name).all()
    return render_template('manager_electrical.html',
                           tickets_with_history=tickets_with_history_and_unit_managers,
                           current_filter=status_filter,
                           current_user=current_user,
                           managers=all_managers, # Pass all managers for general use if needed
                           pagination=paginated_tickets)

@mrwr_bp.route('/manager/update_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def update_production_ticket(ticket_id):
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    ticket.status = request.form['status']
    ticket.approver_mail = request.form.get('approver_mail', '')
    approved_date_time = request.form.get('approved_date_time', '')
    
    if approved_date_time:
        ticket.approved_date_time = datetime.fromisoformat(approved_date_time.replace('T', ' '))
    else:
        ticket.approved_date_time = None
    
    ticket.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    flash('Ticket updated successfully!', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/approve_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def approve_production_ticket(ticket_id):
    """Approve a production ticket"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    if ticket.status != 'open':
        flash('Only open tickets can be approved.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    # Auto-fill approver information
    ticket.status = 'inprogress'
    ticket.approver_mail = current_user.email
    ticket.approved_date_time = datetime.now(timezone.utc)
    ticket.approved_date_time = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Add to history
    
    # Add to history
    add_ticket_history('production', ticket.id, 'approved', current_user.email, current_user.name)
    
    db.session.commit()
    flash('Ticket assinged successfully!', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/approve_ticket_from_email/<int:ticket_id>')
@login_required
def approve_ticket_from_email(ticket_id):
    """Approve a production ticket directly from email link"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    try:
        ticket = ProductionMachine.query.get_or_404(ticket_id)
        
        # Check if ticket is already approved
        if ticket.status == 'approved':
            flash('Ticket is already approved!', 'info')
            return redirect(url_for('mrwr.manager_production'))
        
        # Check if ticket is in open status
        if ticket.status != 'open':
            flash('Only open tickets can be approved!', 'error')
            return redirect(url_for('mrwr.manager_production'))
        
        # Update ticket with approver information
        ticket.status = 'inprogress'
        ticket.approver_mail = current_user.email
        ticket.approved_date_time = datetime.now(timezone.utc)
        
        # Add to history
        add_ticket_history('production', ticket.id, 'approved', current_user.email, current_user.name)
        
        db.session.commit()
        
        print(f"Email Approve - Ticket {ticket_id} approved by {current_user.email}")
        flash(f'Ticket #{ticket_id} approved successfully from email!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error approving ticket from email: {e}")
        flash('Error approving ticket. Please try again.', 'error')
    
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/approve_ticket_from_email/electrical/<int:ticket_id>')
@login_required
def approve_electrical_ticket_from_email(ticket_id):
    """Approve an electrical ticket directly from email link"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    try:
        ticket = Electrical.query.get_or_404(ticket_id)
        
        # Check if ticket is already approved
        if ticket.status == 'approved':
            flash('Ticket is already approved!', 'info')
            return redirect(url_for('mrwr.manager_electrical'))
        
        # Check if ticket is in open status
        if ticket.status != 'open':
            flash('Only open tickets can be approved!', 'error')
            return redirect(url_for('mrwr.manager_electrical'))
        
        # Update ticket with approver information
        ticket.status = 'inprogress'
        ticket.approver_mail = current_user.email
        ticket.approved_date_time = datetime.now(timezone.utc)
        ticket.updated_at = datetime.now(timezone.utc)
        
        # Add to history
        # Add to history
        add_ticket_history('electrical', ticket.id, 'approved', current_user.email, current_user.name)
        
        db.session.commit()
        
        print(f"Email Approve - Electrical Ticket {ticket_id} approved by {current_user.email}")
        flash(f'Electrical Ticket #{ticket_id} approved successfully from email!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error approving electrical ticket from email: {e}")
        flash('Error approving ticket. Please try again.', 'error')
    
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/resolve_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def resolve_production_ticket(ticket_id):
    """Resolve a production ticket"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    resolution_type = request.form.get('resolution_type')
    
    # Allow resolving inprogress tickets OR reopened tickets (open status with approver)
    # For 'not_resolved' status, allow it regardless of current status.
    if resolution_type == 'resolved' and (ticket.status not in ['inprogress', 'open', 'reopened', 'pending'] or (ticket.status == 'open' and not ticket.approver_mail)):
        flash('Only in-progress, open, or reopened tickets can be resolved.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    # Check if current user is the approver of this ticket
    if not (current_user.role == 'super_manager' or ticket.approver_mail == current_user.email):
        flash(f'Only the approver ({ticket.approver_mail}) or a Super Admin can resolve this ticket.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    resolved_reason = request.form.get('resolved_reason', '')
    root_cause = request.form.get('root_cause', '')
    correction = request.form.get('correction', '')
    corrective_action = request.form.get('corrective_action', '')
    knowledge_based = 'knowledge_based' in request.form
    
    # Validate that resolved_reason is provided for both resolution types
    if not resolved_reason.strip():
        flash('Resolution reason is required for both resolved and not resolved tickets.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    if resolution_type == 'resolved':
        ticket.status = 'closed'  # Automatically close when resolved
        ticket.resolved_reason = resolved_reason
        ticket.root_cause = root_cause
        ticket.correction = correction
        ticket.corrective_action = corrective_action
        ticket.knowledge_based = knowledge_based
        ticket.resolved_date_time = datetime.now(timezone.utc)
        ticket.closed_date_time = datetime.now(timezone.utc)
        
        # Set 48-hour grace period
        from datetime import timedelta
        ticket.grace_period_end = datetime.now(timezone.utc) + timedelta(hours=48)
        ticket.is_in_grace_period = True
        
        # Add to history
        add_ticket_history('production', ticket.id, 'resolved', current_user.email, current_user.name, resolved_reason)
        
    elif resolution_type == 'not_resolved':
        ticket.status = 'not_resolved'  # Keep as intermediate status for manual close
        ticket.resolved_reason = resolved_reason
        ticket.root_cause = None # Clear knowledge-based fields if not resolved
        ticket.correction = None
        ticket.corrective_action = None
        ticket.knowledge_based = False
        
        # Add to history
        add_ticket_history('production', ticket.id, 'not_resolved', current_user.email, current_user.name, resolved_reason)
    else:
        flash('Invalid resolution type.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    # Send email notification to ticket creator
    try:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'email': ticket.email,
            'machine_name': ticket.machine_name,
            'vt_machine_number': ticket.vt_machine_number,
            'asset_number': ticket.asset_number,
            'issue_description': ticket.issue_description,
            'priority': ticket.priority,
            'unit': ticket.unit,
            'resolved_reason': ticket.resolved_reason,
            'root_cause': ticket.root_cause,
            'correction': ticket.correction,
            'corrective_action': ticket.corrective_action,
            'knowledge_based': ticket.knowledge_based
        }
        email_result = send_resolve_notification_email_async(ticket_data, resolution_type, current_user.name)
        if email_result:
            print("✅ Resolve notification email sent successfully to ticket creator")
        else:
            print("❌ Resolve notification email failed - check SMTP configuration")
    except Exception as email_error:
        print(f"❌ Failed to send resolve notification email: {email_error}")
        # Don't fail the resolve action if email fails
    
    if resolution_type == 'resolved':
        flash('Ticket resolved and closed successfully!', 'success')
    else:
        flash('Ticket marked as not resolved. Please close it manually.', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/close_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def issue_solved_production_ticket(ticket_id):
    """Mark a production ticket as issue solved"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    if ticket.status != 'not_resolved':
        flash('Only not resolved tickets can be marked as issue solved.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    # Check if current user is the approver of this ticket or a Super Admin
    if not (current_user.role == 'super_manager' or ticket.approver_mail == current_user.email):
        flash(f'Only the approver ({ticket.approver_mail}) or a Super Admin can mark this ticket as issue solved.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    # Get the reason from the form
    issue_solved_reason = request.form.get('issue_solved_reason', '').strip()
    if not issue_solved_reason:
        flash('Please provide a reason for marking the issue as solved.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket.status = 'closed'  # Set to closed as per requirement
    ticket.resolved_reason = issue_solved_reason
    ticket.resolved_date_time = datetime.now(timezone.utc)
    ticket.closed_date_time = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Set 48-hour grace period for reopening
    from datetime import timedelta
    ticket.grace_period_end = datetime.now(timezone.utc) + timedelta(hours=48)
    ticket.is_in_grace_period = True
    
    # Add to history
    add_ticket_history('production', ticket.id, 'issue_solved', current_user.email, current_user.name, issue_solved_reason)
    
    # Send email notification to ticket creator
    try:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'email': ticket.email,
            'machine_name': ticket.machine_name,
            'vt_machine_number': ticket.vt_machine_number,
            'issue_description': ticket.issue_description,
            'priority': ticket.priority,
            'unit': ticket.unit,
            'resolved_reason': ticket.resolved_reason # Use resolved_reason here
        }
        email_result = send_resolve_notification_email_async(ticket_data, 'resolved', current_user.name)
        if email_result:
            print("✅ Issue solved notification email sent successfully to ticket creator")
        else:
            print("❌ Issue solved notification email failed - check SMTP configuration")
    except Exception as email_error:
        print(f"❌ Error sending issue solved notification email: {email_error}")
    
    db.session.commit()
    flash('Ticket marked as issue solved and closed successfully!', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/reopen_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def reopen_production_ticket(ticket_id):
    """Reopen a production ticket during grace period"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    # Check if ticket is in grace period
    if not is_ticket_in_grace_period(ticket):
        flash('Ticket cannot be reopened. Grace period has expired.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    # Check if ticket is closed
    if ticket.status != 'closed':
        flash('Only closed tickets can be reopened.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    reopen_reason = request.form.get('reopen_reason', '').strip()
    if not reopen_reason:
        flash('Reopen reason is required.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    # Reopen the ticket
    ticket.status = 'reopened'
    ticket.is_in_grace_period = False
    ticket.grace_period_end = None
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Add to history
    add_ticket_history('production', ticket.id, 'reopened', current_user.email, current_user.name, reopen_reason)
    
    db.session.commit()
    
    flash(f'Ticket #{ticket_id} reopened successfully!', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/pending_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def pending_production_ticket(ticket_id):
    """Mark a production ticket as pending"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))

    ticket = ProductionMachine.query.get_or_404(ticket_id)
    if not (current_user.role == 'super_manager' or (current_user.role == 'manager' and ticket.approver_mail == current_user.email)):
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    pending_reason = request.form.get('pending_reason', '').strip()

    if not pending_reason:
        flash('A reason is required to mark a ticket as pending.', 'error')
        return redirect(url_for('mrwr.manager_production'))

    ticket.status = 'pending'
    ticket.pending_reason = pending_reason
    ticket.updated_at = datetime.now(timezone.utc)

    add_ticket_history('production', ticket.id, 'pending', current_user.email, current_user.name, pending_reason)
    db.session.commit()

    # Send email notification
    ticket_data = {
        'id': ticket.id,
        'name': ticket.name,
        'email': ticket.email,
        'vt_machine_number': ticket.vt_machine_number,
        'issue_description': ticket.issue_description,
        'pending_reason': pending_reason,
    }
    send_pending_notification_email_async(ticket_data, 'production')

    flash(f'Ticket #{ticket.id} has been marked as pending.', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/delete_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def delete_production_ticket(ticket_id):
    """Delete a production ticket (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    # Store ticket details for flash message
    ticket_details = f"Ticket #{ticket.id} - {ticket.vt_machine_number} ({ticket.name})"
    
    # Delete the ticket
    db.session.delete(ticket)
    db.session.commit()
    
    flash(f'Ticket deleted successfully: {ticket_details}', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/email_configuration')
@login_required
def email_configuration():
    """Email configuration management (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    configurations = EmailConfiguration.query.order_by(EmailConfiguration.unit).all()
    return render_template('email_configuration.html', configurations=configurations)

@mrwr_bp.route('/manager/add_email_config', methods=['POST'])
@login_required
def add_email_config():
    """Add new email configuration (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    unit = request.form['unit']
    email_addresses = request.form['email_addresses']
    is_active = 'is_active' in request.form
    
    # Check if unit already exists
    existing_config = EmailConfiguration.query.filter_by(unit=unit).first()
    if existing_config:
        flash(f'Email configuration for {unit} already exists.', 'error')
        return redirect(url_for('mrwr.email_configuration'))
    
    # Validate email addresses
    emails = [email.strip() for email in email_addresses.split(',') if email.strip()]
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    import re
    
    for email in emails:
        if not re.match(email_regex, email):
            flash(f'Invalid email address: {email}', 'error')
            return redirect(url_for('mrwr.email_configuration'))
    
    # Create new configuration
    config = EmailConfiguration(
        unit=unit,
        email_addresses=email_addresses,
        is_active=is_active
    )
    
    db.session.add(config)
    db.session.commit()
    
    flash(f'Email configuration for {unit} added successfully!', 'success')
    return redirect(url_for('mrwr.email_configuration'))

@mrwr_bp.route('/manager/update_email_config/<int:config_id>', methods=['POST'])
@login_required
def update_email_config(config_id):
    """Update email configuration (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    config = EmailConfiguration.query.get_or_404(config_id)
    
    email_addresses = request.form['email_addresses']
    is_active = 'is_active' in request.form
    
    # Validate email addresses
    emails = [email.strip() for email in email_addresses.split(',') if email.strip()]
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    import re
    
    for email in emails:
        if not re.match(email_regex, email):
            flash(f'Invalid email address: {email}', 'error')
            return redirect(url_for('mrwr.email_configuration'))
    
    # Update configuration
    config.email_addresses = email_addresses
    config.is_active = is_active
    config.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(f'Email configuration for {config.unit} updated successfully!', 'success')
    return redirect(url_for('mrwr.email_configuration'))

@mrwr_bp.route('/manager/delete_email_config/<int:config_id>', methods=['POST'])
@login_required
def delete_email_config(config_id):
    """Delete email configuration (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    config = EmailConfiguration.query.get_or_404(config_id)
    unit = config.unit
    
    db.session.delete(config)
    db.session.commit()
    
    flash(f'Email configuration for {unit} deleted successfully!', 'success')
    return redirect(url_for('mrwr.email_configuration'))

@mrwr_bp.route('/manager/vt_machine_management')
@login_required
def vt_machine_management():
    """VT Machine Number management (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    vt_machines = VTMachineNumber.query.order_by(VTMachineNumber.unit, VTMachineNumber.machine_number).all()
    return render_template('vt_machine_management.html', vt_machines=vt_machines)

@mrwr_bp.route('/manager/add_vt_machine', methods=['POST'])
@login_required
def add_vt_machine():
    """Add new VT machine number (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    machine_number = request.form['machine_number'].strip()
    unit = request.form['unit']
    description = request.form.get('description', '').strip()
    is_active = 'is_active' in request.form
    
    # Check if machine number already exists
    existing_machine = VTMachineNumber.query.filter_by(machine_number=machine_number).first()
    if existing_machine:
        flash(f'VT machine number {machine_number} already exists.', 'error')
        return redirect(url_for('mrwr.vt_machine_management'))
    
    # Create new machine number
    machine = VTMachineNumber(
        machine_number=machine_number,
        unit=unit,
        description=description if description else None,
        is_active=is_active
    )
    
    db.session.add(machine)
    db.session.commit()
    
    flash(f'VT machine number {machine_number} added successfully!', 'success')
    return redirect(url_for('mrwr.vt_machine_management'))

@mrwr_bp.route('/manager/update_vt_machine/<int:machine_id>', methods=['POST'])
@login_required
def update_vt_machine(machine_id):
    """Update VT machine number (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    machine = VTMachineNumber.query.get_or_404(machine_id)
    
    machine_number = request.form['machine_number'].strip()
    unit = request.form['unit']
    description = request.form.get('description', '').strip()
    is_active = 'is_active' in request.form
    
    # Check if machine number already exists (excluding current machine)
    existing_machine = VTMachineNumber.query.filter(
        VTMachineNumber.machine_number == machine_number,
        VTMachineNumber.id != machine_id
    ).first()
    if existing_machine:
        flash(f'VT machine number {machine_number} already exists.', 'error')
        return redirect(url_for('mrwr.vt_machine_management'))
    
    # Update machine number
    machine.machine_number = machine_number
    machine.unit = unit
    machine.description = description if description else None
    machine.is_active = is_active
    machine.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(f'VT machine number {machine_number} updated successfully!', 'success')
    return redirect(url_for('mrwr.vt_machine_management'))

@mrwr_bp.route('/manager/delete_vt_machine/<int:machine_id>', methods=['POST'])
@login_required
def delete_vt_machine(machine_id):
    """Delete VT machine number (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    machine = VTMachineNumber.query.get_or_404(machine_id)
    machine_number = machine.machine_number
    
    db.session.delete(machine)
    db.session.commit()
    
    flash(f'VT machine number {machine_number} deleted successfully!', 'success')
    return redirect(url_for('mrwr.vt_machine_management'))

# Electrical Equipment Management Routes
@mrwr_bp.route('/manager/electrical_equipment_management')
@login_required
def electrical_equipment_management():
    """Electrical Equipment management (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    electrical_equipment = ElectricalEquipment.query.order_by(ElectricalEquipment.unit, ElectricalEquipment.equipment_name).all()
    return render_template('electrical_equipment_management.html', electrical_equipment=electrical_equipment)

@mrwr_bp.route('/manager/add_electrical_equipment', methods=['POST'])
@login_required
def add_electrical_equipment():
    """Add new electrical equipment (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    equipment_name = request.form['equipment_name'].strip()
    unit = request.form['unit'].strip()
    description = request.form.get('description', '').strip()
    is_active = 'is_active' in request.form
    
    # Check if equipment already exists for this unit
    existing_equipment = ElectricalEquipment.query.filter_by(
        equipment_name=equipment_name, 
        unit=unit
    ).first()
    if existing_equipment:
        flash(f'Electrical equipment {equipment_name} already exists for {unit}.', 'error')
        return redirect(url_for('mrwr.electrical_equipment_management'))
    
    # Create new electrical equipment
    equipment = ElectricalEquipment(
        equipment_name=equipment_name,
        unit=unit,
        description=description if description else None,
        is_active=is_active
    )
    
    db.session.add(equipment)
    db.session.commit()
    
    flash(f'Electrical equipment {equipment_name} added successfully!', 'success')
    return redirect(url_for('mrwr.electrical_equipment_management'))

@mrwr_bp.route('/manager/update_electrical_equipment/<int:equipment_id>', methods=['POST'])
@login_required
def update_electrical_equipment(equipment_id):
    """Update electrical equipment (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    equipment = ElectricalEquipment.query.get_or_404(equipment_id)
    equipment_name = request.form['equipment_name'].strip()
    unit = request.form['unit'].strip()
    description = request.form.get('description', '').strip()
    is_active = 'is_active' in request.form
    
    # Check if equipment name already exists for this unit (excluding current equipment)
    existing_equipment = ElectricalEquipment.query.filter(
        ElectricalEquipment.equipment_name == equipment_name,
        ElectricalEquipment.unit == unit,
        ElectricalEquipment.id != equipment_id
    ).first()
    if existing_equipment:
        flash(f'Electrical equipment {equipment_name} already exists for {unit}.', 'error')
        return redirect(url_for('mrwr.electrical_equipment_management'))
    
    # Update electrical equipment
    equipment.equipment_name = equipment_name
    equipment.unit = unit
    equipment.description = description if description else None
    equipment.is_active = is_active
    equipment.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    flash(f'Electrical equipment {equipment_name} updated successfully!', 'success')
    return redirect(url_for('mrwr.electrical_equipment_management'))

@mrwr_bp.route('/manager/delete_electrical_equipment/<int:equipment_id>', methods=['POST'])
@login_required
def delete_electrical_equipment(equipment_id):
    """Delete electrical equipment (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    equipment = ElectricalEquipment.query.get_or_404(equipment_id)
    equipment_name = equipment.equipment_name
    
    db.session.delete(equipment)
    db.session.commit()
    
    flash(f'Electrical equipment {equipment_name} deleted successfully!', 'success')
    return redirect(url_for('mrwr.electrical_equipment_management'))

@mrwr_bp.route('/manager/update_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def update_electrical_ticket(ticket_id):
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    ticket.status = request.form['status']
    ticket.assigned_technician = request.form['assigned_technician']
    ticket.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    flash('Ticket updated successfully!', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/approve_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def approve_electrical_ticket(ticket_id):
    """Approve an electrical ticket"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    
    if ticket.status != 'open':
        flash('Only open tickets can be approved.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket.status = 'inprogress'
    ticket.approver_mail = current_user.email
    ticket.approved_date_time = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Add to history
    add_ticket_history('electrical', ticket.id, 'approved', current_user.email, current_user.name)
    
    db.session.commit()
    flash('Electrical ticket assinged successfully!', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/resolve_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def resolve_electrical_ticket(ticket_id):
    """Resolve an electrical ticket"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    resolution_type = request.form.get('resolution_type')
    
    # Allow resolving inprogress tickets OR reopened tickets (open status with approver)
    # For 'not_resolved' status, allow it regardless of current status.
    if resolution_type == 'resolved' and (ticket.status not in ['inprogress', 'open', 'reopened'] or (ticket.status == 'open' and not ticket.approver_mail)):
        flash('Only in-progress, open, or reopened tickets can be resolved.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    # Check if current user is the approver of this ticket
    if not (current_user.role == 'super_manager' or ticket.approver_mail == current_user.email):
        flash(f'Only the approver ({ticket.approver_mail}) or a Super Admin can resolve this ticket.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    resolved_reason = request.form.get('resolved_reason', '')
    
    # Validate that resolved_reason is provided for both resolution types
    if not resolved_reason.strip():
        flash('Resolution reason is required for both resolved and not resolved tickets.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    if resolution_type == 'resolved':
        ticket.status = 'closed'  # Automatically close when resolved
        ticket.resolved_reason = resolved_reason
        ticket.resolved_date_time = datetime.now(timezone.utc)
        ticket.closed_date_time = datetime.now(timezone.utc)
        
        # Set 48-hour grace period
        from datetime import timedelta
        ticket.grace_period_end = datetime.now(timezone.utc) + timedelta(hours=48)
        ticket.is_in_grace_period = True
        
        # Add to history
        add_ticket_history('electrical', ticket.id, 'resolved', current_user.email, current_user.name, resolved_reason)
        
    elif resolution_type == 'not_resolved':
        ticket.status = 'not_resolved'  # Keep as intermediate status for manual close
        ticket.resolved_reason = resolved_reason
        
        # Add to history
        add_ticket_history('electrical', ticket.id, 'not_resolved', current_user.email, current_user.name, resolved_reason)
    else:
        flash('Invalid resolution type.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    # Send email notification to ticket creator
    try:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'email': ticket.email,
            'equipment_name': ticket.equipment_name,
            'issue_description': ticket.issue_description,
            'priority': ticket.priority,
            'unit': ticket.unit,
            'resolved_reason': ticket.resolved_reason # Use resolved_reason here
        }
        email_result = send_electrical_resolve_notification_email_async(ticket_data, resolution_type, current_user.name)
        if email_result:
            print("✅ Electrical resolve notification email sent successfully to ticket creator")
        else:
            print("❌ Electrical resolve notification email failed - check SMTP configuration")
    except Exception as email_error:
        print(f"❌ Failed to send electrical resolve notification email: {email_error}")
        # Don't fail the resolve action if email fails
    
    if resolution_type == 'resolved':
        flash('Electrical ticket resolved and closed successfully!', 'success')
    else:
        flash('Electrical ticket marked as not resolved. Please close it manually.', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/close_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def issue_solved_electrical_ticket(ticket_id):
    """Mark an electrical ticket as issue solved"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    
    if ticket.status != 'not_resolved':
        flash('Only not resolved tickets can be marked as issue solved.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    # Check if current user is the approver of this ticket
    if ticket.approver_mail != current_user.email:
        flash(f'Only the approver ({ticket.approver_mail}) can mark this ticket as issue solved.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    # Get the reason from the form
    issue_solved_reason = request.form.get('issue_solved_reason', '').strip()
    if not issue_solved_reason:
        flash('Please provide a reason for marking the issue as solved.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket.status = 'closed'  # Set to closed as per requirement
    ticket.resolved_reason = issue_solved_reason
    ticket.resolved_date_time = datetime.now(timezone.utc)
    ticket.closed_date_time = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Set 48-hour grace period for reopening
    from datetime import timedelta
    ticket.grace_period_end = datetime.now(timezone.utc) + timedelta(hours=48)
    ticket.is_in_grace_period = True
    
    # Add to history
    add_ticket_history('electrical', ticket.id, 'issue_solved', current_user.email, current_user.name, issue_solved_reason)
    
    # Send email notification to ticket creator
    try:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'email': ticket.email,
            'equipment_name': ticket.equipment_name,
            'issue_description': ticket.issue_description,
            'priority': ticket.priority,
            'unit': ticket.unit,
            'resolved_reason': ticket.resolved_reason # Use resolved_reason here
        }
        email_result = send_electrical_resolve_notification_email_async(ticket_data, 'resolved', current_user.name)
        if email_result:
            print("✅ Issue solved notification email sent successfully to ticket creator")
        else:
            print("❌ Issue solved notification email failed - check SMTP configuration")
    except Exception as email_error:
        print(f"❌ Error sending issue solved notification email: {email_error}")
    
    db.session.commit()
    flash('Electrical ticket marked as issue solved and closed successfully!', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/reopen_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def reopen_electrical_ticket(ticket_id):
    """Reopen an electrical ticket during grace period"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    
    # Check if ticket is in grace period
    if not is_ticket_in_grace_period(ticket):
        flash('Ticket cannot be reopened. Grace period has expired.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    # Check if ticket is closed
    if ticket.status != 'closed':
        flash('Only closed tickets can be reopened.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    reopen_reason = request.form.get('reopen_reason', '').strip()
    if not reopen_reason:
        flash('Reopen reason is required.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    # Reopen the ticket
    ticket.status = 'reopened'
    ticket.is_in_grace_period = False
    ticket.grace_period_end = None
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Add to history
    add_ticket_history('electrical', ticket.id, 'reopened', current_user.email, current_user.name, reopen_reason)
    
    db.session.commit()
    
    flash(f'Electrical Ticket #{ticket_id} reopened successfully!', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/pending_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def pending_electrical_ticket(ticket_id):
    """Mark an electrical ticket as pending"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))

    ticket = Electrical.query.get_or_404(ticket_id)
    if not (current_user.role == 'super_manager' or (current_user.role == 'manager' and ticket.approver_mail == current_user.email)):
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    pending_reason = request.form.get('pending_reason', '').strip()

    if not pending_reason:
        flash('A reason is required to mark a ticket as pending.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))

    ticket.status = 'pending'
    ticket.pending_reason = pending_reason
    ticket.updated_at = datetime.now(timezone.utc)

    add_ticket_history('electrical', ticket.id, 'pending', current_user.email, current_user.name, pending_reason)
    db.session.commit()

    # Send email notification
    ticket_data = {
        'id': ticket.id,
        'name': ticket.name,
        'email': ticket.email,
        'equipment_name': ticket.equipment_name,
        'issue_description': ticket.issue_description,
        'pending_reason': pending_reason,
    }
    send_pending_notification_email_async(ticket_data, 'electrical')

    flash(f'Ticket #{ticket.id} has been marked as pending.', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/reopen_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def user_reopen_production_ticket(ticket_id):
    """User reopens their own production ticket during grace period"""
    print(f"🔄 User reopen production ticket {ticket_id} - User: {current_user.email}")
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    # Check if user owns the ticket
    if ticket.user_id != current_user.id:
        flash('You can only reopen your own tickets.', 'error')
        return redirect(url_for('mrwr.my_production_tickets'))
    
    # Check if ticket is in grace period
    if not is_ticket_in_grace_period(ticket):
        flash('Ticket cannot be reopened. Grace period has expired.', 'error')
        return redirect(url_for('mrwr.my_production_tickets'))
    
    # Check if ticket is closed
    if ticket.status != 'closed':
        flash('Only closed tickets can be reopened.', 'error')
        return redirect(url_for('mrwr.my_production_tickets'))
    
    reopen_reason = request.form.get('reopen_reason', '').strip()
    if not reopen_reason:
        flash('Reopen reason is required.', 'error')
        return redirect(url_for('mrwr.my_production_tickets'))
    
    # Reopen the ticket
    print(f"✅ Reopening ticket {ticket_id} - Status: {ticket.status} -> reopened")
    ticket.status = 'reopened'
    ticket.is_in_grace_period = False
    ticket.grace_period_end = None
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Add to history
    add_ticket_history('production', ticket.id, 'reopened', current_user.email, current_user.name, reopen_reason)
    
    db.session.commit()
    print(f"✅ Ticket {ticket_id} reopened successfully in database")
    
    # Send email notification to managers about ticket reopening
    try:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'email': ticket.email,
            'vt_machine_number': ticket.vt_machine_number,
            'asset_number': ticket.asset_number,
            'issue_description': ticket.issue_description,
            'priority': ticket.priority,
            'unit': ticket.unit,
            'reopen_reason': reopen_reason
        }
        email_result = send_reopen_notification_email_async(ticket_data, 'production')
        if email_result:
            print("✅ Reopen notification email sent successfully to managers")
        else:
            print("❌ Reopen notification email failed - check SMTP configuration")
    except Exception as email_error:
        print(f"❌ Failed to send reopen notification email: {email_error}")
        # Don't fail the reopen action if email fails
    
    flash(f'Your ticket #{ticket_id} has been reopened successfully!', 'success')
    return redirect(url_for('mrwr.my_production_tickets'))

@mrwr_bp.route('/reopen_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def user_reopen_electrical_ticket(ticket_id):
    """User reopens their own electrical ticket during grace period"""
    ticket = Electrical.query.get_or_404(ticket_id)
    
    # Check if user owns the ticket
    if ticket.user_id != current_user.id:
        flash('You can only reopen your own tickets.', 'error')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    # Check if ticket is in grace period
    if not is_ticket_in_grace_period(ticket):
        flash('Ticket cannot be reopened. Grace period has expired.', 'error')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    # Check if ticket is closed
    if ticket.status != 'closed':
        flash('Only closed tickets can be reopened.', 'error')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    reopen_reason = request.form.get('reopen_reason', '').strip()
    if not reopen_reason:
        flash('Reopen reason is required.', 'error')
        return redirect(url_for('mrwr.my_electrical_tickets'))
    
    # Reopen the ticket
    ticket.status = 'reopened'
    ticket.is_in_grace_period = False
    ticket.grace_period_end = None
    ticket.updated_at = datetime.now(timezone.utc)
    
    # Add to history
    add_ticket_history('electrical', ticket.id, 'reopened', current_user.email, current_user.name, reopen_reason)
    
    db.session.commit()
    
    # Send email notification to managers about electrical ticket reopening
    try:
        ticket_data = {
            'id': ticket.id,
            'name': ticket.name,
            'email': ticket.email,
            'equipment_name': ticket.equipment_name,
            'issue_description': ticket.issue_description,
            'priority': ticket.priority,
            'unit': ticket.unit,
            'reopen_reason': reopen_reason
        }
        email_result = send_reopen_notification_email_async(ticket_data, 'electrical')
        if email_result:
            print("✅ Electrical reopen notification email sent successfully to managers")
        else:
            print("❌ Electrical reopen notification email failed - check SMTP configuration")
    except Exception as email_error:
        print(f"❌ Failed to send electrical reopen notification email: {email_error}")
        # Don't fail the reopen action if email fails
    
    flash(f'Your electrical ticket #{ticket_id} has been reopened successfully!', 'success')
    return redirect(url_for('mrwr.my_electrical_tickets'))

@mrwr_bp.route('/manager/delete_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def delete_electrical_ticket(ticket_id):
    """Delete an electrical ticket (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    
    # Store ticket details for flash message
    ticket_details = f"Ticket #{ticket.id} - {ticket.equipment_name} ({ticket.name})"
    
    # Delete the ticket
    db.session.delete(ticket)
    db.session.commit()
    
    flash(f'Electrical ticket deleted successfully: {ticket_details}', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/hold_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def hold_production_ticket(ticket_id):
    """Hold a production ticket"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    if not (current_user.role == 'super_manager' or (current_user.role == 'manager' and ticket.approver_mail == current_user.email)):
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    hold_reason = request.form.get('hold_reason', '').strip()

    if not hold_reason:
        flash('A reason is required to place a ticket on hold.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket.status = 'hold'
    ticket.held_by = current_user.email
    ticket.hold_reason = hold_reason
    ticket.updated_at = datetime.now(timezone.utc)
    
    add_ticket_history('production', ticket.id, 'hold', current_user.email, current_user.name, hold_reason)
    
    db.session.commit()
    
    # Send email notification to supermanager
    supermanager = User.query.filter_by(role='super_manager').first()
    if supermanager:
        ticket_data = {
            'id': ticket.id,
            'vt_machine_number': ticket.vt_machine_number,
            'held_by': current_user.name,
            'hold_reason': hold_reason
        }
        send_hold_notification_email_async(supermanager.email, ticket_data, 'production')

    flash(f'Ticket #{ticket.id} has been put on hold.', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/reassign_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def reassign_production_ticket(ticket_id):
    """Reassign a production ticket (Super Admin only)"""
    print(f"DEBUG: Reassign production ticket route hit for ticket ID: {ticket_id}")
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    new_manager_id = request.form.get('new_manager')
    print(f"DEBUG: new_manager_id from form: {new_manager_id}")
    
    try:
        new_manager_id = int(new_manager_id)
    except (ValueError, TypeError):
        flash('Invalid manager selected.', 'error')
        print(f"DEBUG: Invalid manager ID format: {new_manager_id}")
        return redirect(url_for('mrwr.manager_production'))

    new_manager = User.query.get(new_manager_id)
    
    if not new_manager or new_manager.role not in ['manager', 'super_manager']:
        flash('Invalid manager selected.', 'error')
        print(f"DEBUG: Invalid manager selected or role: {new_manager_id}")
        return redirect(url_for('mrwr.manager_production'))

    ticket.approver_mail = new_manager.email
    ticket.status = 'open' # Re-open the ticket for the new manager
    ticket.held_by = None
    ticket.updated_at = datetime.now(timezone.utc)
    
    add_ticket_history('production', ticket.id, 'reassigned', current_user.email, current_user.name, f"Reassigned to {new_manager.name}")
    
    db.session.commit()
    print(f"DEBUG: Ticket {ticket.id} reassigned to {new_manager.email} in DB.")
    
    # Send email notification to the new manager
    ticket_data = {
        'id': ticket.id,
        'vt_machine_number': ticket.vt_machine_number,
        'assigned_by': current_user.name
    }
    # Assuming send_reassign_notification_email_async is defined elsewhere or will be added.
    # For now, just print a debug message.
    send_reassign_notification_email_async(new_manager.email, ticket_data, 'production')

    flash(f'Ticket #{ticket.id} has been reassigned to {new_manager.name}.', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/hold_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def hold_electrical_ticket(ticket_id):
    """Hold an electrical ticket"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    if not (current_user.role == 'super_manager' or (current_user.role == 'manager' and ticket.approver_mail == current_user.email)):
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    hold_reason = request.form.get('hold_reason', '').strip()

    if not hold_reason:
        flash('A reason is required to place a ticket on hold.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket.status = 'hold'
    ticket.held_by = current_user.email
    ticket.hold_reason = hold_reason
    ticket.updated_at = datetime.now(timezone.utc)
    
    add_ticket_history('electrical', ticket.id, 'hold', current_user.email, current_user.name, hold_reason)
    
    db.session.commit()
    
    # Send email notification to supermanager
    supermanager = User.query.filter_by(role='super_manager').first()
    if supermanager:
        ticket_data = {
            'id': ticket.id,
            'equipment_name': ticket.equipment_name,
            'held_by': current_user.name,
            'hold_reason': hold_reason
        }
        send_hold_notification_email_async(supermanager.email, ticket_data, 'electrical')

    flash(f'Ticket #{ticket.id} has been put on hold.', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/reassign_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def reassign_electrical_ticket(ticket_id):
    """Reassign an electrical ticket (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    new_manager_id = request.form.get('new_manager')
    
    try:
        new_manager_id = int(new_manager_id)
    except (ValueError, TypeError):
        flash('Invalid manager selected.', 'error')
        print(f"DEBUG: Invalid manager ID format: {new_manager_id}")
        return redirect(url_for('mrwr.manager_electrical'))

    new_manager = User.query.get(new_manager_id)
    
    if not new_manager or new_manager.role not in ['manager', 'super_manager']:
        flash('Invalid manager selected.', 'error')
        print(f"DEBUG: Invalid manager selected or role: {new_manager_id}")
        return redirect(url_for('mrwr.manager_electrical'))

    ticket.approver_mail = new_manager.email
    ticket.status = 'open' # Re-open the ticket for the new manager
    ticket.held_by = None
    ticket.updated_at = datetime.now(timezone.utc)
    
    add_ticket_history('electrical', ticket.id, 'reassigned', current_user.email, current_user.name, f"Reassigned to {new_manager.name}")
    
    db.session.commit()
    
    print(f"DEBUG: Electrical Ticket {ticket.id} reassigned to {new_manager.email} in DB.")
    # Send email notification to the new manager
    ticket_data = {
        'id': ticket.id,
        'equipment_name': ticket.equipment_name,
        'assigned_by': current_user.name
    }
    # Assuming send_reassign_notification_email_async is defined elsewhere or will be added.
    # For now, just print a debug message.
    send_reassign_notification_email_async(new_manager.email, ticket_data, 'electrical')

    flash(f'Ticket #{ticket.id} has been reassigned to {new_manager.name}.', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/resign_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def resign_production_ticket(ticket_id):
    """Resign from a production ticket, returning it to the open pool"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_production'))

    ticket = ProductionMachine.query.get_or_404(ticket_id)

    if ticket.approver_mail != current_user.email:
        flash('You can only resign from tickets assigned to you.', 'error')
        return redirect(url_for('mrwr.manager_production'))

    previous_approver = ticket.approver_mail

    ticket.status = 'open'
    ticket.approver_mail = None
    ticket.approved_date_time = None
    ticket.updated_at = datetime.now(timezone.utc)

    add_ticket_history('production', ticket.id, 'resigned', current_user.email, current_user.name, f"Resigned from ticket. Previous approver: {previous_approver}")

    db.session.commit()

    flash(f'You have resigned from ticket #{ticket.id}. It is now open for assignment.', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/resign_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def resign_electrical_ticket(ticket_id):
    """Resign from an electrical ticket, returning it to the open pool"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))

    ticket = Electrical.query.get_or_404(ticket_id)

    if ticket.approver_mail != current_user.email:
        flash('You can only resign from tickets assigned to you.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))

    previous_approver = ticket.approver_mail

    ticket.status = 'open'
    ticket.approver_mail = None
    ticket.approved_date_time = None
    ticket.updated_at = datetime.now(timezone.utc)

    add_ticket_history('electrical', ticket.id, 'resigned', current_user.email, current_user.name, f"Resigned from ticket. Previous approver: {previous_approver}")

    db.session.commit()

    flash(f'You have resigned from ticket #{ticket.id}. It is now open for assignment.', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/take_back_ticket/production/<int:ticket_id>', methods=['POST'])
@login_required
def take_back_production_ticket(ticket_id):
    """Take back a production ticket that was on hold"""
    if current_user.role != 'manager':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket = ProductionMachine.query.get_or_404(ticket_id)
    
    if ticket.status != 'hold' or ticket.held_by != current_user.email:
        flash('You can only take back tickets that you placed on hold.', 'error')
        return redirect(url_for('mrwr.manager_production'))
    
    ticket.status = 'in_progress'
    ticket.approver_mail = current_user.email
    ticket.updated_at = datetime.now(timezone.utc)
    
    add_ticket_history('production', ticket.id, 'resumed', current_user.email, current_user.name, "Ticket taken back by manager")
    
    db.session.commit()
    
    # Send email notification to supermanager
    ticket_data = {
        'id': ticket.id,
        'vt_machine_number': ticket.vt_machine_number,
        'resumed_by': current_user.name
    }
    send_resume_notification_email_async(ticket_data, 'production')

    flash(f'Ticket #{ticket.id} has been taken back and is now in progress.', 'success')
    return redirect(url_for('mrwr.manager_production'))

@mrwr_bp.route('/manager/take_back_ticket/electrical/<int:ticket_id>', methods=['POST'])
@login_required
def take_back_electrical_ticket(ticket_id):
    """Take back an electrical ticket that was on hold"""
    if current_user.role != 'manager':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket = Electrical.query.get_or_404(ticket_id)
    
    if ticket.status != 'hold' or ticket.held_by != current_user.email:
        flash('You can only take back tickets that you placed on hold.', 'error')
        return redirect(url_for('mrwr.manager_electrical'))
    
    ticket.status = 'in_progress'
    ticket.approver_mail = current_user.email
    ticket.updated_at = datetime.now(timezone.utc)
    
    add_ticket_history('electrical', ticket.id, 'resumed', current_user.email, current_user.name, "Ticket taken back by manager")
    
    db.session.commit()
    
    # Send email notification to supermanager
    ticket_data = {
        'id': ticket.id,
        'equipment_name': ticket.equipment_name,
        'resumed_by': current_user.name
    }
    send_resume_notification_email_async(ticket_data, 'electrical')

    flash(f'Ticket #{ticket.id} has been taken back and is now in progress.', 'success')
    return redirect(url_for('mrwr.manager_electrical'))

@mrwr_bp.route('/manager/temp_reset_password', methods=['GET', 'POST'])
@login_required
def temp_reset_password():
    """Temporary route to reset a user's password (Super Admin only)"""
    if current_user.role != 'super_manager':
        flash('Access denied. Super Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['new_password']

        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            flash(f'Password for {email} updated successfully!', 'success')
        else:
            flash(f'User with email {email} not found.', 'error')
        return redirect(url_for('mrwr.temp_reset_password'))
    
    return render_template('temp_reset_password.html')

@mrwr_bp.route('/manager/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))

    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            employee_id = request.form.get('employee_id', '')
            department = request.form.get('department', '')
            password = request.form['password']
            unit = request.form['unit']
            role = request.form['role']
            
            print(f"Add User - Received data: name={name}, email={email}, employee_id={employee_id}, department={department}, unit={unit}, role={role}, password={'*' * len(password)}")
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists!', 'error')
                print(f"Add User - Email {email} already exists, returning to form.")
                return redirect(url_for('mrwr.add_user')) # Ensure redirect on error
            
            user = User(name=name, email=email, employee_id=employee_id, department=department, unit=unit, role=role)
            user.set_password(password)
            
            db.session.add(user)
            print(f"Add User - User {email} added to session. Attempting to commit...")
            db.session.commit()
            print(f"Add User - User {email} created successfully with ID {user.id}")
            flash('User added successfully!', 'success')
            
            return redirect(url_for('mrwr.add_user'))
 
        except Exception as e:
            db.session.rollback()
            import traceback
            print(f"Add User - Error during user creation: {e}")
            print(traceback.format_exc()) # Print full traceback for debugging
            flash(f'Error adding user: {e}. Please try again.', 'error')
            return redirect(url_for('mrwr.add_user')) # Ensure redirect on error

    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('add_user.html', users=all_users, show_add_user_form=True)

@mrwr_bp.route('/manager/update_user', methods=['POST'])
@login_required
def update_user():
    """Update a user (Admin and Super Admin only)"""
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    user_id = request.form.get('user_id')
    name = request.form.get('name')
    email = request.form.get('email')
    employee_id = request.form.get('employee_id', '')
    department = request.form.get('department', '')
    unit = request.form.get('unit')
    role = request.form.get('role')
    password = request.form.get('password')
    
    if not all([user_id, name, email, unit, role]):
        flash('All required fields must be filled.', 'error')
        return redirect(url_for('mrwr.add_user'))
    
    try:
        user = User.query.get(int(user_id))
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('mrwr.add_user'))
        
        # Check if email is already taken by another user
        existing_user = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_user:
            flash('Email address is already in use by another user.', 'error')
            return redirect(url_for('mrwr.add_user'))
        
        # Update user data
        user.name = name
        user.email = email
        user.employee_id = employee_id
        user.department = department
        user.unit = unit
        user.role = role
        
        # Update password only if provided
        if password and password.strip():
            user.set_password(password)
        
        db.session.commit()
        flash(f'User "{user.name}" has been updated successfully.', 'success')
        print(f"Update User - User {user.email} (ID: {user_id}) updated successfully")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating user: {e}")
        flash('Error updating user. Please try again.', 'error')
    
    return redirect(url_for('mrwr.add_user'))

@mrwr_bp.route('/manager/delete_user', methods=['POST'])
@login_required
def delete_user():
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))
    
    try:
        user_id = request.form['user_id']
        user_to_delete = User.query.get_or_404(user_id)
        
        # Prevent manager from deleting themselves
        if user_to_delete.id == current_user.id:
            flash('You cannot delete your own account!', 'error')
            return redirect(url_for('mrwr.add_user'))
        
        # Delete related tickets first (if any)
        ProductionMachine.query.filter_by(user_id=user_id).delete()
        Electrical.query.filter_by(user_id=user_id).delete()
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        flash(f'User "{user_to_delete.name}" has been deleted successfully!', 'success')
        print(f"Delete User - User {user_to_delete.email} (ID: {user_id}) deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user. Please try again.', 'error')
        print(f"Delete User - Error: {e}")
    
    return redirect(url_for('mrwr.add_user'))

@mrwr_bp.route('/manager/export/production/csv')
@login_required
def export_production_tickets_csv():
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))

    status_filter = request.args.get('status', 'all')
    
    query = ProductionMachine.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    tickets = query.order_by(ProductionMachine.created_at.desc()).all()

    si = io.StringIO()
    cw = csv.writer(si)

    # Write header
    header = [
        "Ticket ID", "User Name", "User Email", "Employee ID", "Department", "Unit",
        "VT Machine Details", "Issue Description", "Priority", "Status",
        "Created Date", "Approver Mail", "Approved Date Time", "Resolved Reason",
        "ROOT CAUSE", "Correction", "Corrective Action", "Knowledge Based",
        "Asset Number", "Ticket Closed Date and Time"
    ]
    cw.writerow(header)

    # Write data
    for ticket in tickets:
        row = [
            ticket.id,
            ticket.name,
            ticket.email,
            ticket.employee_id,
            ticket.department,
            ticket.unit,
            ticket.vt_machine_number,
            ticket.issue_description,
            ticket.priority,
            ticket.status,
            ticket.created_at.isoformat() if ticket.created_at else '',
            ticket.approver_mail,
            ticket.approved_date_time.isoformat() if ticket.approved_date_time else '',
            ticket.resolved_reason,
            ticket.root_cause,
            ticket.correction,
            ticket.corrective_action,
            'Yes' if ticket.knowledge_based else 'No',
            ticket.asset_number,
            ticket.closed_date_time.isoformat() if ticket.closed_date_time else ''
        ]
        cw.writerow(row)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=production_tickets.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@mrwr_bp.route('/manager/export/electrical/csv')
@login_required
def export_electrical_tickets_csv():
    if current_user.role not in ['manager', 'super_manager']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('mrwr.dashboard'))

    status_filter = request.args.get('status', 'all')
    
    query = Electrical.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    tickets = query.order_by(Electrical.created_at.desc()).all()

    si = io.StringIO()
    cw = csv.writer(si)

    # Write header
    header = [
        "Ticket ID", "User Name", "User Email", "Employee ID", "Department", "Unit",
        "Equipment Name", "Issue Description", "Priority", "Status",
        "Created Date", "Approver Mail", "Approved Date Time", "Resolved Reason",
        "Ticket Closed Date and Time"
    ]
    cw.writerow(header)

    # Write data
    for ticket in tickets:
        row = [
            ticket.id,
            ticket.name,
            ticket.email,
            ticket.employee_id,
            ticket.department,
            ticket.unit,
            ticket.equipment_name,
            ticket.issue_description,
            ticket.priority,
            ticket.status,
            ticket.created_at.isoformat() if ticket.created_at else '',
            ticket.approver_mail,
            ticket.approved_date_time.isoformat() if ticket.approved_date_time else '',
            ticket.resolved_reason,
            ticket.closed_date_time.isoformat() if ticket.closed_date_time else ''
        ]
        cw.writerow(row)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=electrical_tickets.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# Register the blueprint
app.register_blueprint(mrwr_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Ensure manager user exists and has the correct password
        manager = User.query.filter_by(email='manager@maintenance.com').first()
        if manager:
            db.session.delete(manager)
            db.session.commit()
            print("Existing manager user deleted to ensure fresh password hash.")
            
        manager = User(name='Admin', email='manager@maintenance.com', employee_id='ADM001', department='IT Department', unit='Unit-2', role='manager')
        manager.set_password('manager123')
        db.session.add(manager)
        db.session.commit()
        print("Admin user created/recreated with password: manager@maintenance.com / manager123")
        
        # Ensure supermanager user exists and has the correct password
        supermanager = User.query.filter_by(email='supermanager@maintenance.com').first()
        if supermanager:
            db.session.delete(supermanager)
            db.session.commit()
            print("Existing supermanager user deleted to ensure fresh password hash.")
            
        supermanager = User(name='Super Admin', email='supermanager@maintenance.com', employee_id='SADM001', department='IT Department', unit='Unit-1', role='super_manager')
        supermanager.set_password('supermanager123')
        db.session.add(supermanager)
        db.session.commit()
        print("Super Admin user created/recreated with password: supermanager@maintenance.com / supermanager123")

    app.run(debug=True)
