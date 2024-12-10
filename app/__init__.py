from flask import Flask
from flask_pymongo import PyMongo
from config import Config

mongo = PyMongo()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mongo.init_app(app)

    with app.app_context():
        from .routes import bp as main_bp
        app.register_blueprint(main_bp)

    return app
