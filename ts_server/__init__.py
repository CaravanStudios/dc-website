import os
import secrets

from flask import send_from_directory, abort
from jinja2 import ChoiceLoader, FileSystemLoader

from server import create_app as create_base_app
from ts_server.routes import static

EXTENDED_STATIC = os.path.join(os.path.dirname(__file__), 'dist')
BASE_STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server', 'dist')
EXTENDED_TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')

def create_app():
  app = create_base_app()

  # Override config
  from ts_server.app_env.techsoup import Config
  app.config.from_object(Config)
  app.config['TRUSTED_DOMAINS'] = os.environ.get('TRUSTED_DOMAINS', [])

  if not os.environ.get('SECRET_KEY'):
    random_secret_key = secrets.token_urlsafe(32)
    app.logger.warning(f"No SECRET_KEY set in env. Using a random key for this session: {random_secret_key}")
    app.config['SECRET_KEY'] = random_secret_key
  else:
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

  # Set config for Google Form URL and field mapping
  app.config['GOOGLE_FORM_URL'] = os.environ.get('GOOGLE_FORM_URL', '')
  app.config['FORM_FIELD_MAPPING_JSON'] = os.environ.get('FORM_FIELD_MAPPING_JSON', '')

  # Load templates: extended -> base
  app.jinja_loader = ChoiceLoader([
    FileSystemLoader(EXTENDED_TEMPLATES),
    app.jinja_loader,
  ])

  app.jinja_loader = ChoiceLoader([
    FileSystemLoader(EXTENDED_TEMPLATES),
    app.jinja_loader,
  ])

  app.jinja_env.globals['BASE_HTML'] = 'base.html'

  # Remove existing static route to avoid conflict
  if 'static' in app.view_functions:
    app.logger.warning(f"Removing existing static route {app.view_functions['static']}")
    app.blueprints.pop('static')
    del app.view_functions['static']

  # Step 5: Add custom static route with fallback
  @app.route('/<path:filename>', endpoint='static')
  def static_fallback(filename):
    app.logger.info(f"Request for path: '{filename}'")
    extended_path = os.path.join(EXTENDED_STATIC, filename)
    if os.path.isfile(extended_path):
      return send_from_directory(EXTENDED_STATIC, filename)

    base_path = os.path.join(BASE_STATIC, filename)
    if os.path.isfile(base_path):
      return send_from_directory(BASE_STATIC, filename)

    abort(404)

  # Register base blueprints as fallback
  try:
    from ts_server.routes import register_blueprints as register_ts_blueprints
    register_ts_blueprints(app)

  except ImportError:
    pass

  return app
