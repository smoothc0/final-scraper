from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_id = db.Column(db.String(100))
    plan = db.Column(db.String(50), nullable=False)
    limit = db.Column(db.Integer, nullable=False)
    emails_scraped = db.Column(db.Integer, default=0)
    renewal_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Subscription {self.plan} for user {self.user_id}>'