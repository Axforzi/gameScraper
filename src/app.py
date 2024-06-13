from sys import prefix
from flask import Flask

app = Flask(__name__)

#ROUTES
from routes.index import index
app.register_blueprint(index)

if __name__ == "__main__":
    app.run(debug=True)