from datetime import datetime, timedelta, timezone

import jwt
from flask import request, current_app, make_response

import server.lib.render as lib_render
from server.routes.static import bp

TOKEN_TTL = timedelta(hours=24)
LOCAL_HOSTNAMES = ('localhost', '127.0.0.1')


@bp.route('/resources')
def resources():
  domain = request.host.lower()  # e.g., datacommons.techsoup.org
  hostname = domain.split(':')[0]
  trusted = current_app.config.get("TRUSTED_DOMAINS", [])
  if domain not in trusted and hostname not in LOCAL_HOSTNAMES:
    current_app.logger.info(f'Resources: untrusted domain {domain}')
    return "Unauthorized domain", 403
  token = jwt.encode({
      "domain": domain,
      "exp": datetime.now(timezone.utc) + TOKEN_TTL
  },
                     current_app.config["SECRET_KEY"],
                     algorithm="HS256")
  resp = make_response(lib_render.render_page('resources.html', "resources.html"))
  resp.set_cookie("api_token",
                  token,
                  max_age=int(TOKEN_TTL.total_seconds()),
                  httponly=True,
                  secure=True,
                  samesite='Strict')
  return resp
