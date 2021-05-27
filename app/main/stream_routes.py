from flask import (
    flash, g, current_app, render_template, request, session, Response
)

from jinja2.exceptions import TemplateNotFound
import functools
import json
import redis

from app.main.auth_routes import login_required
from app.bokeh_layouts import get_layout


def get_redis():
    """ Define a connection to the redis database """
    if not current_app.redis:
        current_app.redis = redis.Redis(host='3.131.117.61', port=5001, password='thisisthepasswordtotheredisserver', decode_responses=True)
    try:
        current_app.redis.ping()  # ping redis server
    except Exception as e:
        flash("Failed to connect to Redis: {}".format(e))
        current_app.redis = None
        return False
    g.redis = current_app.redis
    return True


def redis_required(view):
    """ Decorator to validate Redis connection """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_redis():
            return view(**kwargs)
        else:
            return "", 404
    return wrapped_view


def read_stream(stream_name):
    """
    Reads data from a Redis Stream since last read (if last read data is stored in session).
    Redis returns nested lists in which key-value pairs are consecutive elements.
    Converts this output into json bytes to package into an HTTP response.
    Should decorate calling function with @redis_required.
    """
    # get ID to start reading from, if any
    idx = 'last_read_{}'.format(stream_name)
    last_read = session.get(idx)
    if not last_read:
        session[idx] = current_app.redis.xrevrange('stream:'+stream_name, count=1)[0][0]

    # Get data from redis server
    stream = current_app.redis.xread({'stream:'+stream_name: session[idx]}, None, 0)  # BLOCK 0
    if not stream:  # no new data
        return
    session[idx] = stream[0][1][-1][0]

    # get keys, which are every other element in first data list
    keys = stream[0][1][0][1].keys()
    output = {key: [] for key in keys}

    # loop through stream data
    for data in stream[0][1]:
        # data[0] is the timestamp ID
        d = data[1]  # data dict
        for key in keys:
            output[key].append(float(d[key]))  # convert to float and append

    return json.dumps(output)


# import blueprint
from app.main import streams


@streams.route('/', methods=['GET', 'POST'])
@streams.route('/index', methods=('GET', 'POST'))
@login_required
def index():
    commands = {'Start': 'START', 'Stop': 'STOP', 'refresh':'REFRESH'}
    return render_template('/index.html', commands=commands)


@streams.route('/stream', methods=('GET', 'POST'))
@login_required
@redis_required
def stream():
    stream_name = request.args.get('name')
    stream_type = g.redis.hget('info:'+stream_name, 'type')

    # get stream page template according to stream type
    template_path = '/streams/{}.html'.format(stream_type)
    try:
        return render_template(template_path, stream_name=stream_name)
    except TemplateNotFound as e:
        return render_template('/error.html', error="Template Not Found: \"{}\"".format(template_path))


@streams.route('/stream/plot_layout', methods=('GET', 'POST'))
@login_required
@redis_required
def plot_layout():
    """ Returns the layout JSON for the bokeh plot """
    stream_name = request.args.get('name')
    #stream_type = g.redis.hget('info:'+stream_name, 'type')

    # Get full layout json string for this stream
    layout = get_layout(stream_name)

    resp = Response(response=layout, content_type='application/json')
    return resp


@streams.route('/stream/update', methods=('GET', 'POST'))
@login_required
@redis_required  # yes technically, but will this overhead cause too much latency?
def plot_update():
    """ Returns the json to update a plot """
    stream_name = request.args.get('name')
    #stream_type = g.redis.execute_command('hmget info:{} type'.format(stream_name))[0]

    data = read_stream(stream_name)  # read data from redis
    if data:
        resp = Response(response=data, content_type='application/json')
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    else:
        return "", 304
