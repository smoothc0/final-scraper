import os
import sys
import threading
from datetime import datetime, timedelta
from time import sleep

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_required, current_user, login_user
from werkzeug.security import generate_password_hash, check_password_hash
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest

# Local imports
from db import db, User, Subscription
from auth import auth_bp
from scraper.email_crawler import EmailScraper

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# Register blueprints
app.register_blueprint(auth_bp)

# Plan configurations
PLANS = {
    'starter': {'price': 7, 'limit': 100, 'name': 'Starter'},
    'pro': {'price': 14, 'limit': 500, 'name': 'Pro'},
    'elite': {'price': 21, 'limit': 2000, 'name': 'Elite'}
}

# Health check endpoint
@app.route('/health')
def health_check():
    try:
        User.query.limit(1).all()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def initialize_database():
    """Initialize database with admin user if needed"""
    with app.app_context():
        try:
            db.create_all()
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
            
            if not User.query.filter_by(email=admin_email).first():
                admin_user = User(
                    email=admin_email,
                    password=generate_password_hash(admin_password, method='pbkdf2:sha256'),
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("Admin user created successfully")
        except Exception as e:
            print(f"Database initialization failed: {str(e)}", file=sys.stderr)
            raise

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Application routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html', plans=PLANS)

@app.route('/dashboard')
@login_required
def dashboard():
    subscription = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not subscription:
        flash('Please subscribe to a plan to access dashboard', 'error')
        return redirect(url_for('pricing'))
    
    return render_template('dashboard.html',
                         plan=subscription.plan,
                         limit=subscription.limit,
                         emails_scraped=subscription.emails_scraped)

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
        flash('You have reached your monthly limit', 'error')
        return redirect(url_for('pricing'))
    
    target = request.form.get('target', '').strip()
    if not target:
        flash('Please enter a valid website URL', 'error')
        return redirect(url_for('dashboard'))
    
    def scrape_task():
        try:
            scraper = EmailScraper(max_pages=5)
            emails = scraper.scrape_website(target)
            
            # Update subscription
            subscription.emails_scraped += len(emails)
            db.session.commit()
            
            # Store results
            print(f"Scraped {len(emails)} emails from {target}")
            
        except Exception as e:
            print(f"Scraping failed: {str(e)}", file=sys.stderr)
    
    threading.Thread(target=scrape_task).start()
    flash('Scraping started. Results will appear shortly.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    subscriptions = Subscription.query.all()
    return render_template('admin.html', users=users, subscriptions=subscriptions)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Initialize the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    try:
        initialize_database()
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Failed to start application: {str(e)}", file=sys.stderr)
        sys.exit(1)