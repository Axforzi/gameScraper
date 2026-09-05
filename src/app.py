from sys import prefix
from flask import Flask

app = Flask(__name__)

#ROUTES
from routes.index import index
app.register_blueprint(index)

from waitress import serve

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000)
