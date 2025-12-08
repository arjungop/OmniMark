from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime
from database import load_users, save_users, get_user_context
from utils.auth_utils import hash_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        users = load_users()
        
        if email in users and users[email]['password'] == hash_password(password):
            session['user'] = email
            
            # Check if user has completed onboarding
            context = get_user_context(email)
            if not context:
                return redirect(url_for('main.onboarding'))
            
            return redirect(url_for('main.dashboard'))
        
        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        users = load_users()
        
        if email in users:
            return render_template('register.html', error="Email already registered")
        
        users[email] = {
            'name': name,
            'email': email,
            'password': hash_password(password),
            'created_at': datetime.now().isoformat()
        }
        
        save_users(users)
        session['user'] = email
        
        return redirect(url_for('main.onboarding'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('auth.login'))
