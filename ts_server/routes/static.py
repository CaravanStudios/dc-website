import jwt
from flask import request, current_app, make_response

import server.lib.render as lib_render
from server.routes.static import bp


@bp.route('/resources')
def resources():
  domain = request.host.lower()  # e.g., contact.yoursite.com
  current_app.logger.info(f'Resources: {domain}')
  current_app.logger.info(f'Trusted domains: {current_app.config.get("TRUSTED_DOMAINS", [])}')
  trusted = current_app.config.get("TRUSTED_DOMAINS", [])
  is_localhost = "localhost" in domain or domain.startswith("127.0.0.1")
  if domain not in trusted and not is_localhost:
    return "Unauthorized domain", 403
  token = jwt.encode({"domain": domain}, current_app.config["SECRET_KEY"], algorithm="HS256")
  resp = make_response(lib_render.render_page('resources.html', "resources.html"))
  resp.set_cookie("api_token", token, httponly=True, secure=True, samesite='Strict')
  return resp
