# app.py - Updated
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_required, current_user
from db import db, User, Subscription
from auth import auth_bp
from werkzeug.security import generate_password_hash
import os
from datetime import datetime, timedelta
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest
from scraper.email_crawler import EmailScraper
import threading
from time import sleep

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# Initialize extensions
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# Register blueprints
app.register_blueprint(auth_bp)

# Plans configuration
PLANS = {
    'starter': {'price': 7, 'limit': 100, 'name': 'Starter'},
    'pro': {'price': 14, 'limit': 500, 'name': 'Pro'},
    'elite': {'price': 21, 'limit': 2000, 'name': 'Elite'}
}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def initialize_database():
    db.create_all()
    # Create admin user if not exists
    if not User.query.filter_by(email='admin@example.com').first():
        admin_user = User(
            email='admin@example.com',
            password=generate_password_hash('adminpassword', method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

def create_subscription(user_id, plan_name):
    plan = PLANS.get(plan_name)
    if not plan:
        return None
    
    subscription = Subscription(
        user_id=user_id,
        plan=plan['name'],
        limit=plan['limit'],
        emails_scraped=0,
        is_active=True
    )
    db.session.add(subscription)
    db.session.commit()
    return subscription

# Routes remain mostly the same but with improved error handling
@app.route('/scrape', methods=['POST'])
@login_required
def scrape_emails():
    subscription = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not subscription:
        flash('Please subscribe to a plan to use the scraper', 'error')
        return redirect(url_for('pricing'))
    
    if not subscription.is_valid():
        flash('Your subscription has expired', 'error')
        return redirect(url_for('pricing'))
    
    if subscription.emails_scraped >= subscription.limit:
        flash('You have reached your monthly limit. Please upgrade your plan.', 'error')
        return redirect(url_for('pricing'))
    
    target = request.form.get('target', '').strip()
    if not target:
        flash('Please enter a valid website URL or keyword', 'error')
        return redirect(url_for('dashboard'))
    
    def scrape_task():
        try:
            scraper = EmailScraper(max_pages=5)
            emails = scraper.scrape_website(target)
            
            # Update subscription
            subscription.emails_scraped += len(emails)
            db.session.commit()
            
            # In a real app, you'd store these emails and show to user
            print(f"Found {len(emails)} emails")
            
        except Exception as e:
            print(f"Scraping error: {str(e)}")
    
    # Run in background thread
    thread = threading.Thread(target=scrape_task)
    thread.start()
    
    flash('Scraping started in the background. Results will be available shortly.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)