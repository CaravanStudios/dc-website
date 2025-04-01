import jwt
from flask import request, jsonify, current_app

def domain_jwt_required(f):
    def wrapper(*args, **kwargs):
        token = request.cookies.get("api_token")
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            domain = decoded.get("domain")
            if domain not in current_app.config.get('TRUSTED_DOMAINS', []):
                return jsonify({'error': 'Unauthorized domain'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper