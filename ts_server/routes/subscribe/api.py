from flask import Blueprint, request, jsonify, current_app
from ts_server.shared.form_submitter import submit_to_google_form

from ts_server.shared.auth.utils import domain_jwt_required

subscribe_api = Blueprint('subscribe_api', __name__, url_prefix='/api/newsletter')

@subscribe_api.route('/subscribe', methods=['POST'])
@domain_jwt_required
def submit_subscription():
    data = request.get_json()

    if not data or 'email' not in data or 'first_name' not in data or 'last_name' not in data or 'organization' not in data:
        return jsonify({'error': 'Name, email, first name, last name, organization are required'}), 400

    email = data['email']
    first_name = data['first_name']
    last_name = data['last_name']
    organization = data['organization']

    response = submit_to_google_form(email,first_name, last_name, organization, is_subscribed=True)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to subscribe'}), 500

    current_app.logger.info(f"Subscription request for {email} with response: {response.status_code}")

    return jsonify({'message': 'Successfully subscribed'}), 200


@subscribe_api.route('/unsubscribe', methods=['POST'])
@domain_jwt_required
def unsubscribe():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400

    email = data['email']
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    organization = data.get('organization', '')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    response = submit_to_google_form(email, first_name, last_name, organization, is_subscribed=False)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to unsubscribe'}), 500

    current_app.logger.info(f"Unsubscription request for {email} with response: {response.status_code}")

    return jsonify({'message': 'Successfully unsubscribed'}), 200
