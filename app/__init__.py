from flask import Flask, send_from_directory
import redis
import os

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY='dev')
    app.redis = redis.Redis(host='3.131.117.61', port=5001, password='thisisthepasswordtotheredisserver', decode_responses=True)
    try:
        app.redis.ping()  # ping redis server
    except Exception as e:
        print("Could not connect to redis: {}".format(e))

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # add basic favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # register blueprints
    from . import auth
    app.register_blueprint(auth.bp)

    from . import streams
    app.register_blueprint(streams.bp)
    app.add_url_rule('/', endpoint='index')

    # initialize data ingestion layer


    return app
