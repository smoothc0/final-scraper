from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from db import db, User, Subscription
from auth import auth_bp
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)

# PayPal configuration
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET')
PAYPAL_ENVIRONMENT = SandboxEnvironment(client_id=PAYPAL_CLIENT_ID, client_secret=PAYPAL_SECRET)
paypal_client = PayPalHttpClient(PAYPAL_ENVIRONMENT)

# Plan configurations
PLANS = {
    'starter': {'price': 7, 'limit': 100, 'name': 'Starter'},
    'pro': {'price': 14, 'limit': 500, 'name': 'Pro'},
    'elite': {'price': 21, 'limit': 2000, 'name': 'Elite'}
}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html', plans=PLANS)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/checkout/<plan>')
@login_required
def checkout(plan):
    if plan not in PLANS:
        flash('Invalid plan selected', 'error')
        return redirect(url_for('pricing'))
    
    plan_details = PLANS[plan]
    
    # Create PayPal order
    request = OrdersCreateRequest()
    request.prefer('return=representation')
    request.request_body({
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": str(plan_details['price']),
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": str(plan_details['price'])
                        }
                    }
                },
                "items": [
                    {
                        "name": f"{plan_details['name']} Plan",
                        "description": f"Monthly subscription for {plan_details['limit']} emails",
                        "quantity": "1",
                        "unit_amount": {
                            "currency_code": "USD",
                            "value": str(plan_details['price'])
                        }
                    }
                ]
            }
        ],
        "application_context": {
            "return_url": url_for('thank_you', _external=True),
            "cancel_url": url_for('pricing', _external=True),
            "brand_name": "AI Email Scraper",
            "user_action": "SUBSCRIBE_NOW"
        }
    })
    
    try:
        response = paypal_client.execute(request)
        approval_url = next(link.href for link in response.result.links if link.rel == 'approve')
        return redirect(approval_url)
    except Exception as e:
        print(e)
        flash('Error creating PayPal order', 'error')
        return redirect(url_for('pricing'))

@app.route('/thank-you')
@login_required
def thank_you():
    # In a real app, you'd verify the payment here via webhook
    # For demo, we'll just update the user's subscription
    return render_template('thank_you.html')

@app.route('/dashboard')
@login_required
def dashboard():
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    if not subscription:
        flash('Please subscribe to a plan to access the dashboard', 'error')
        return redirect(url_for('pricing'))
    
    return render_template('dashboard.html', 
                         plan=subscription.plan,
                         limit=subscription.limit,
                         emails_scraped=subscription.emails_scraped)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    subscriptions = Subscription.query.all()
    return render_template('admin.html', users=users, subscriptions=subscriptions)

@app.route('/scrape', methods=['POST'])
@login_required
def scrape_emails():
    # Implement your email scraping logic here
    # For demo purposes, we'll just increment the count
    subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    if not subscription:
        flash('Please subscribe to a plan to use the scraper', 'error')
        return redirect(url_for('pricing'))
    
    if subscription.emails_scraped >= subscription.limit:
        flash('You have reached your monthly limit. Please upgrade your plan.', 'error')
        return redirect(url_for('pricing'))
    
    # Simulate scraping
    subscription.emails_scraped += 10
    db.session.commit()
    
    flash('Successfully scraped 10 emails (demo)', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(email='admin@example.com').first():
            admin_user = User(
                email='admin@example.com',
                password=generate_password_hash('adminpassword'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)