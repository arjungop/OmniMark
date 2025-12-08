from flask import Blueprint, render_template, session, redirect, url_for
from database import get_user_context, load_users, load_data
from utils.auth_utils import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    email = session['user']
    context = get_user_context(email)
    
    if not context:
        return redirect(url_for('main.onboarding'))
    
    # Get user data
    users = load_users()
    user = users.get(email, {})
    
    # Get app data
    user_data = load_data()
    
    # Use the PRO dashboard
    return render_template('dashboard.html', context=context, user=user, user_data=user_data)

@main_bp.route('/onboarding')
@login_required
def onboarding():
    email = session['user']
    users = load_users()
    user = users.get(email, {})
    return render_template('onboarding.html', user=user)
