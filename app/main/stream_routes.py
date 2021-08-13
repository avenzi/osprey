from flask import current_app, session, render_template, request, Response, redirect, url_for, flash

from jinja2.exceptions import TemplateNotFound
from bokeh.embed import json_item
from json import dumps, loads
from time import time
import os

from lib.database import DatabaseError, DatabaseTimeoutError, DatabaseConnectionError
from local import server_stream_config

# import blueprint + socket
from app.main import streams, socketio

from app.main.utils import get_database, check_filename
from app.main.auth_routes import auth_required

# todo: how to emit socketIO messages in a Flask route? The socketIO messages need to know what
#  room to emit to, which will be the room with the SID of the socket. However the Flask routes
#  do not know what socket was active on the page that sent it. Maybe sent the corresponding socket SID
#  in a custom header with every request??


@streams.route('/', methods=['GET', 'POST'])
@streams.route('/index', methods=['GET', 'POST'])
@auth_required
def index():
    return render_template('/index.html')


@auth_required
@streams.route('/stream', methods=('GET', 'POST'))
def stream():
    group_name = request.args.get('group')

    # get stream page template
    file = server_stream_config.pages.get(group_name)
    if not file:
        err = "No stream page configured for: {}".format(group_name)
        print(err)
        flash(err)
        return redirect(url_for('index'))

    template_path = '/streams/{}'.format(file)

    try:
        database = get_database()
        if not database:  # no database found for this session
            print("Database not found for session: {}".format(session.sid))
            return redirect(url_for('index'))
        info = database.get_group(group_name)
        return render_template(template_path, info=info, title=group_name)
    except TemplateNotFound as e:
        return render_template('/error.html', error="Template Not Found: \"{}\"".format(template_path))
    except DatabaseError as e:
        print("Could not read from database for template '{}'.".format(template_path))
        return redirect(url_for('index'))


@auth_required
@streams.route('/stream/plot_layout', methods=('GET', 'POST'))
def plot_layout():
    """ Returns the layout JSON for the bokeh plot """
    group_name = request.args.get('group')

    try:
        # get info dict of all streams in this group
        info = get_database().get_group(group_name)
    except DatabaseError as e:
        print('Database Error occurred when trying to read stream info: {}'.format(e))
        return

    # get bokeh layout function associated with this group
    create_layout = server_stream_config.bokeh_layouts.get(group_name)
    if not create_layout:
        err = "No layout function specified for group '{}'".format(group_name)
        flash(err)
        return err, 404

    try:
        layout = create_layout(info)  # bokeh layout object
    except Exception as e:
        err = "Failed to create layout for group {}. {}: {}".format(group_name, e.__class__.__name__, e)
        flash(err)
        return err, 500

    json_layout = dumps(json_item(layout))

    resp = Response(response=json_layout, content_type='application/json')
    return resp


@auth_required
@streams.route('/stream/update', methods=('GET', 'POST'))
def plot_update():
    """ Returns the json to update a bokeh plot """
    request_id = request.args.get('id')
    request_format = request.args.get('format')

    try:
        database = get_database()
        start = time()
        if not database:
            return "Database not found for this session", 503
        if not request_format or request_format == 'series':
            data = database.read_data(request_id, to_json=True, max_time=5, downsample=True)
            #print("READ TIME: ", time()-start)
            #print()
        elif request_format == 'snapshot':
            data = database.read_snapshot(request_id, to_json=True)
        else:
            err = 'Bokeh request for data specified an unknown request format: {}'.format(request_format)
            print(err)
            return err, 500
    except DatabaseTimeoutError:
        #print("TIMEOUT TIME: ", time()-start)
        #print()
        return "Database query timed out", 503
    except DatabaseConnectionError:
        return "Lost connection to database", 500
    except DatabaseError as e:
        return str(e), 500

    if data:
        resp = Response(response=data, content_type='application/json')
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    else:
        return "", 304  # not modified (no new data)


@auth_required
@streams.route('/stream/widgets', methods=('GET', 'POST'))
def widget_update():
    """
    Received Bokeh widget updates from a browser.
    Passes the update to the namespace of the associated streamer.
    """
    request_id = request.args.get('id')
    widget_dict = request.json

    # The id specifies which streamer/analyzer to send this info to.
    # JSON is automatically converted to python types
    socketio.emit('json', widget_dict, namespace='/'+request_id)
    return "", 200

