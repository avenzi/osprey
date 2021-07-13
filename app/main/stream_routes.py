from flask import flash, current_app, session, render_template, request, Response

from jinja2.exceptions import TemplateNotFound
from bokeh.embed import json_item
from json import dumps, loads

from app.main.auth_routes import login_required
from lib.database import DatabaseError
from local import server_stream_config

# import blueprint + socket
from app.main import streams, socketio


@login_required
@streams.route('/', methods=['GET', 'POST'])
@streams.route('/index', methods=('GET', 'POST'))
def index():
    return render_template('/index.html')


@login_required
@streams.route('/stream', methods=('GET', 'POST'))
def stream():
    group_name = request.args.get('group')

    # get stream page template
    file = server_stream_config.pages.get(group_name)
    if not file:
        print("No stream page configured for: {}".format(group_name))
        return "", 404

    template_path = '/streams/{}'.format(file)

    try:
        info = current_app.database.read_group(group_name)
        return render_template(template_path, info=info, title=group_name)
    except TemplateNotFound as e:
        return render_template('/error.html', error="Template Not Found: \"{}\"".format(template_path))
    except DatabaseError as e:
        print("Could not read from database for template '{}'.".format(template_path))


@login_required
@streams.route('/stream/plot_layout', methods=('GET', 'POST'))
def plot_layout():
    """ Returns the layout JSON for the bokeh plot """
    group_name = request.args.get('group')

    try:
        # get info dict of all streams in this group
        info = current_app.database.read_group(group_name)
    except DatabaseError as e:
        print('Database Error occurred when trying to read stream info: {}'.format(e))
        return

    # get bokeh layout function associated with this group
    create_layout = server_stream_config.bokeh_layouts.get(group_name)
    if not create_layout:
        err = "No layout function specified for group '{}'".format(group_name)
        return err, 404

    try:
        layout = create_layout(info)  # bokeh layout object
    except Exception as e:
        err = "Failed to create layout for group {}. {}: {}".format(group_name, e.__class__.__name__, e)
        flash(err)
        print(err)
        return err, 404

    json_layout = dumps(json_item(layout))

    resp = Response(response=json_layout, content_type='application/json')
    return resp


@login_required
@streams.route('/stream/update', methods=('GET', 'POST'))
def plot_update():
    """ Returns the json to update a bokeh plot """
    request_id = request.args.get('id')
    request_format = request.args.get('format')

    try:
        if not request_format or request_format == 'series':
            data = current_app.database.read_data(request_id, to_json=True, max_time=5)
        elif request_format == 'snapshot':
            data = current_app.database.read_snapshot(request_id, to_json=True)
        else:
            print('Bokeh request for data specified an unknown request format')
            return "", 404
    except DatabaseError as e:
        print("Database Error: {}".format(e))
        return "", 500

    if data:
        resp = Response(response=data, content_type='application/json')
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    else:
        return "", 304  # not modified (no new data)


@login_required
@streams.route('/stream/widgets', methods=('GET', 'POST'))
def widget_update():
    """
    Received Bokeh widget updates from a browser.
    Passes the update to the namespace of the associated streamer.
    """
    request_id = request.args.get('id')
    widget_dict = request.json

    # use the ID as the socket namespace on which to send this info
    # JSON is automatically converted to python types
    socketio.emit('json', widget_dict, namespace='/'+request_id)
    return "", 200

