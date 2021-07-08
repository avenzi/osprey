from functools import wraps
from flask import (
    Blueprint, flash, g, current_app, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

# import blueprint
from app.main import auth


@auth.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        red = current_app.redis

        error = None
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif red.get(username):
            error = 'User {} is already registered.'.format(username)

        if error is None:
            red.set(username, generate_password_hash(password))
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')


@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        submit_username = request.form['username']
        submit_password = request.form['password']

        error = None
        if submit_password != 'password':
            error = 'Incorrect Password'

        #if pass_hash is None:
            #error = 'Username does not exist.'
        #if not check_password_hash(pass_hash, submit_password):
            #error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['username'] = submit_username
            return redirect(url_for('index'))

        flash(error)
    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    session.clear()
    return render_template('auth/logged_out.html')


def login_required(view):
    """ Decorator to validate user login before accessing a route """
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get('username') is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view