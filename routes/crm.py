from flask import Blueprint, jsonify, request
from database import crm
from utils.auth_utils import login_required

crm_bp = Blueprint('crm', __name__)

@crm_bp.route('/api/crm/contacts', methods=['GET'])
@login_required
def get_crm_contacts():
    """Get all contacts from SheetDB CRM"""
    try:
        contacts = crm.get_all_contacts()
        return jsonify({'success': True, 'contacts': contacts, 'count': len(contacts)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/contact', methods=['POST'])
@login_required
def add_crm_contact():
    """Add new contact to SheetDB CRM"""
    try:
        contact_data = request.json
        result = crm.add_contact(contact_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/contact/<email>', methods=['GET'])
@login_required
def get_crm_contact(email):
    """Get contact by email from SheetDB CRM"""
    try:
        contact = crm.get_contact(email)
        if contact:
            return jsonify({'success': True, 'contact': contact})
        else:
            return jsonify({'success': False, 'error': 'Contact not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/contact/<email>', methods=['PATCH'])
@login_required
def update_crm_contact(email):
    """Update contact in SheetDB CRM"""
    try:
        updates = request.json
        result = crm.update_contact(email, updates)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/campaign', methods=['POST'])
@login_required
def log_crm_campaign():
    """Log campaign to SheetDB CRM"""
    try:
        campaign_data = request.json
        result = crm.log_campaign(campaign_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/event', methods=['POST'])
@login_required
def log_crm_event():
    """Log event to SheetDB CRM"""
    try:
        event_data = request.json
        result = crm.log_event(event_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/analytics', methods=['GET'])
@login_required
def get_crm_analytics():
    """Get analytics from SheetDB CRM"""
    try:
        analytics = crm.get_analytics_summary()
        return jsonify({'success': True, 'analytics': analytics})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@crm_bp.route('/api/crm/bulk-import', methods=['POST'])
@login_required
def bulk_import_contacts():
    """Bulk import contacts to SheetDB CRM"""
    try:
        contacts = request.json.get('contacts', [])
        result = crm.bulk_add_contacts(contacts)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
