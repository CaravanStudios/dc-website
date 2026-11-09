from flask import Blueprint, request, jsonify, current_app
from ts_server.shared.form_submitter import submit_to_google_form

from ts_server.shared.auth.utils import domain_jwt_required

subscribe_api = Blueprint('subscribe_api', __name__, url_prefix='/api/newsletter')

FIELDS = ('email', 'first_name', 'last_name', 'organization')


def _read_fields():
  """Return dict of stripped string fields from JSON body, or None if body is not an object."""
  data = request.get_json(silent=True)
  if not isinstance(data, dict):
    return None
  return {k: str(data.get(k) or '').strip() for k in FIELDS}


def _submit(fields, is_subscribed, error_message):
  """Submit to Google Form. Return error response, or None on success."""
  try:
    submit_to_google_form(fields['email'],
                          fields['first_name'],
                          fields['last_name'],
                          fields['organization'],
                          is_subscribed=is_subscribed)
  except ValueError:
    # Input is checked before, so ValueError here = missing form config.
    current_app.logger.exception('Newsletter form not configured')
    return jsonify({'error': error_message}), 500
  except RuntimeError:
    current_app.logger.exception('Newsletter form submission failed')
    return jsonify({'error': error_message}), 502
  return None


@subscribe_api.route('/subscribe', methods=['POST'])
@domain_jwt_required
def submit_subscription():
  fields = _read_fields()
  if not fields or not all(fields.values()):
    return jsonify({'error': 'Name, email, first name, last name, organization are required'}), 400

  error = _submit(fields, True, 'Failed to subscribe')
  if error:
    return error

  current_app.logger.info('Newsletter subscription submitted')
  return jsonify({'message': 'Successfully subscribed'}), 200


@subscribe_api.route('/unsubscribe', methods=['POST'])
@domain_jwt_required
def unsubscribe():
  fields = _read_fields()
  if not fields or not fields['email']:
    return jsonify({'error': 'Email is required'}), 400

  error = _submit(fields, False, 'Failed to unsubscribe')
  if error:
    return error

  current_app.logger.info('Newsletter unsubscription submitted')
  return jsonify({'message': 'Successfully unsubscribed'}), 200
