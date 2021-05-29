from flask import (
    flash, g, current_app, render_template, request, session, Response
)

from jinja2.exceptions import TemplateNotFound
import functools

from app.main.auth_routes import login_required
from app.bokeh_layouts import get_layout
from app import Database

# import blueprint
from app.main import streams

# import browser buttons
from app.main.events import BUTTONS


@login_required
@streams.route('/', methods=['GET', 'POST'])
@streams.route('/index', methods=('GET', 'POST'))
def index():
    return render_template('/index.html', buttons=BUTTONS)


@login_required
@streams.route('/stream', methods=('GET', 'POST'))
def stream():
    stream_id = request.args.get('id')
    try:
        info = current_app.database.read_info(stream_id)  # get info dict
    except Database.Error as e:
        print('Database Error occurred when trying to read stream info: {}'.format(e))
        return

    # get stream page template according to stream type
    template_path = '/streams/{}.html'.format(info['type'])
    try:
        return render_template(template_path)
    except TemplateNotFound as e:
        return render_template('/error.html', error="Template Not Found: \"{}\"".format(template_path))


@login_required
@streams.route('/stream/plot_layout', methods=('GET', 'POST'))
def plot_layout():
    """ Returns the layout JSON for the bokeh plot """
    stream_id = request.args.get('id')

    try:
        info = current_app.database.read_info(stream_id)  # get info dict
    except Database.Error as e:
        print('Database Error occurred when trying to read stream info: {}'.format(e))
        return

    stream_type = info['type']

    if stream_type == 'plot':  # bokeh plot
        layout = get_layout(info)  # Get full layout json string for this stream
        resp = Response(response=layout, content_type='application/json')
    else:
        print("Stream of unknown type '{}' requested a plot_layout.".format(stream_type))
        resp = render_template()
        return

    return resp


@login_required
@streams.route('/stream/update', methods=('GET', 'POST'))
def plot_update():
    """ Returns the json to update a plot """
    stream_id = request.args.get('id')

    try:
        key = 'last_read_{}'.format(stream_id)  # key in session for last read
        data, last_read = current_app.database.read_data_since(stream_id, last_read=session.get(key), to_json=True)
        session[key] = last_read
    except Database.Error:
        return "", 404

    if data:
        resp = Response(response=data, content_type='application/json')
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    else:
        return "", 304  # not modified (no new data)
