import os
import re
import secrets

from flask import send_from_directory, abort
from jinja2 import ChoiceLoader, FileSystemLoader

from server import create_app as create_base_app
from ts_server.routes import static

EXTENDED_STATIC = os.path.join(os.path.dirname(__file__), 'dist')
BASE_STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server', 'dist')
EXTENDED_TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')


def parse_domains(value):
  """Parse TRUSTED_DOMAINS env: "a.com,b.com" or "['a.com', 'b.com']"."""
  return [d.lower() for d in re.findall(r"[^\s,\[\]'\"]+", value or '')]


def create_app():
  app = create_base_app()

  # Override config
  from ts_server.app_env.techsoup import Config
  app.config.from_object(Config)
  app.config['TRUSTED_DOMAINS'] = parse_domains(os.environ.get('TRUSTED_DOMAINS'))

  if not os.environ.get('SECRET_KEY'):
    app.logger.warning("No SECRET_KEY set in env. Using a random key for this process.")
    app.config['SECRET_KEY'] = secrets.token_urlsafe(32)
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
