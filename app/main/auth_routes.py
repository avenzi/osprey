from functools import wraps
from flask import (
    Blueprint, flash, g, current_app, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

# import blueprint
from app.main import auth
from app.main.utils import (
    log, info, warn, error, catch_errors
)


@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=('GET', 'POST'))
def login():
    """ Uses the Flask App SECRET_KEY to act as an authentication key """
    if request.method == 'POST':
        submit_password = request.form['password']

        error = None
        if submit_password != current_app.config['SECRET_KEY']:
            error = 'Incorrect Authentication Key'

        #if pass_hash is None:
            #error = 'Username does not exist.'
        #if not check_password_hash(pass_hash, submit_password):
            #error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['authenticated'] = True
            return redirect(url_for('index'))

        flash(error)
    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    session.clear()
    return render_template('auth/logged_out.html')


def auth_required(view):
    """ Decorator to validate user login before accessing a route """
    @wraps(view)
    def wrapped_view(**kwargs):
        print("AUTH: ", session.get('authenticated'))
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view