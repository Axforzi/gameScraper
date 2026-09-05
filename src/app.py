import os
from sys import prefix
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFProtect, CSRFError

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    app.config['SECRET_KEY'] = 'dev-only-insecure-secret'
    app.logger.warning(
        'SECRET_KEY not set; using an insecure dev fallback. '
        'Set SECRET_KEY in the environment before deploying.'
    )

# CSRF protection for all POST endpoints
CSRFProtect(app)

#ROUTES
from routes.index import index
app.register_blueprint(index)

@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    return jsonify({'error': 'CSRF validation failed'}), 400

from waitress import serve

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000)
