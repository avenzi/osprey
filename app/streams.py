from flask import (
    Blueprint, flash, g, current_app, redirect, render_template, request, session, url_for,
    Response
)
from jinja2.exceptions import TemplateNotFound

from app.auth import login_required
import app.bokeh_layouts as layouts

bp = Blueprint('streams', __name__)


@bp.before_request
def before_request():
    """ Get connection to Redis server one each request """
    g.redis = current_app.redis


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=('GET', 'POST'))
@login_required
def index():
    return render_template('/index.html')


@bp.route('/stream', methods=('GET', 'POST'))
@login_required
def stream():
    stream_name = request.args.get('name')
    stream_type = g.redis.execute_command('hmget info:{} type'.format(stream_name))[0]

    # get stream page template according to stream type
    template_path = 'streams/{}.html'.format(stream_type)
    try:
        return render_template(template_path, stream_name=stream_name)
    except TemplateNotFound as e:
        return render_template('/error.html', error="Template Not Found: \"{}\"".format(template_path))


@bp.route('/plot_layout', methods=('GET', 'POST'))
@login_required
def plot_layout():
    """ Returns the layout JSON for the bokeh plot """
    stream_name = request.args.get('name')
    #stream_type = g.redis.execute_command('hget info:{} type'.format(stream_name))[0]

    # Get full layout json string for this stream
    # TODO: Not hard-code the various stream types here.
    #  It should be able to look through /boheh_layouts and find the right layout
    if stream_name == 'TestStreamer':
        layout = layouts.TestStreamer.lay
    elif stream_name == 'SenseStreamer':
        layout = layouts.SenseStreamer.lay
    else:
        raise Exception("Layout for {} not found".format(stream_name))

    resp = Response(response=layout, content_type='application/json')
    return resp


@bp.route('/update', methods=('GET', 'POST'))
@login_required
def plot_update():
    """ Returns the json to update a plot """
    stream_name = request.args.get('name')
    #stream_type = g.redis.execute_command('hmget info:{} type'.format(stream_name))[0]

    # get ID to start reading from
    last_read = session.get('last_read')
    if not last_read:
        session['last_read'] = current_app.redis.execute_command('XREVRANGE stream:{} + - COUNT 1'.format(stream_name))[1][0]
        print('LAST READ', session['last_read'])

    # Get data from redis server
    data = current_app.redis.execute_command('XREAD STREAMS stream:{} {}'.format(stream_name, session['last_read']))
    print("DATA", data)
    #data = json.dumps(data)  # convert to json
    resp = Response(response=data, content_type='application/json')
    resp.headers['Cache-Control'] = 'no-store'
    return resp
