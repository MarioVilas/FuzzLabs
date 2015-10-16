#!/usr/bin/python

import sys

import re
import json
import time
import syslog
import logging
import httplib
import requests
import threading
from functools import wraps
from flask import request
from flask import url_for
from flask import redirect
from flask import make_response
from flask import render_template
from flask import send_from_directory
from flask import Flask, make_response
from flask.ext.login import LoginManager
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask.ext.login import current_user
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from OpenSSL import SSL

from classes.database import Base
from classes.database.User import User
from classes.database.Engine import Engine
from classes.database.Job import Job

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

whitelist = {}
whitelist["id"]        = '^[0-9]*$'
whitelist["job_id"]    = '^[a-f0-9]{32}$'
whitelist["datetime"]  = '^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}$'
whitelist["username"]  = '[^@]+@[^@]+\.[^@]+'
whitelist["address"]   = '^[a-zA-Z0-9\.-_]{1,255}$'
whitelist["port"]      = '^[0-9]{1,5}$'

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

SECRET_KEY              = 'ufC*o%|V3Rji5nGIK^J7D8sNlgizXdN1eg-+i47of8YP4LdVN*zHk-^M*RrH'
SESSION_COOKIE_SECURE   = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///etc/webserver.db'

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.config.from_object(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
db = SQLAlchemy(app)
Base.Base.metadata.create_all(db.engine)
db.session.commit()

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class Response:

    def __init__(self, status = None, message = None, data = None):
        self.status  = status
        self.message = message
        self.data    = data

    def get(self):
        rv = {}
        if self.status: rv["status"] = self.status
        if self.message: rv["message"] = self.message
        if self.data: rv["data"] = self.data
        return json.dumps(rv)

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def do_validate(type, value):
    global whitelist
    if type not in whitelist: return True
    if not re.match(whitelist[type], value): return False
    return True

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def validate(f):
    @wraps(f)
    def validate_input(**kwargs):
        global whitelist
        url_vars = []
        for p in kwargs: url_vars.append(p)
        for key in url_vars:
            if whitelist.get(key):
                if not do_validate(key, kwargs[key]):
                    syslog.syslog(syslog.LOG_WARNING,
                                  "parameter %s failed validation from: %s" %\
                                  (key, request.remote_addr))
                    return redirect(url_for("root"))
        url_params = request.args.items()
        if len(url_params) > 0:
            for key, value in url_params:
                if key not in whitelist: continue
                if not do_validate(key, value):
                    syslog.syslog(syslog.LOG_WARNING,
                                  "parameter %s failed validation from: %s" %\
                                  (key, request.remote_addr))
                    return redirect(url_for("root"))
        if request.method == "POST":
            for key, value in request.form.iteritems():
                if not do_validate(key.encode('ascii', 'ignore'), 
                                   value.encode('ascii', 'ignore')):
                    syslog.syslog(syslog.LOG_WARNING,
                                  "parameter %s failed validation from: %s" %\
                                  (key, request.remote_addr))
                    return redirect(url_for("root"))
        return f(**kwargs)
    return validate_input

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def add_response_headers(headers={}):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resp = make_response(f(*args, **kwargs))
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp
        return decorated_function
    return decorator

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def api_headers(f):
    @wraps(f)
    @add_response_headers({'Server': 'dcnws'})
    @add_response_headers({'Content-Type': 'application/json'})
    @add_response_headers({'Cache-Control': 'no-cache, no-store, must-revalidate'})
    @add_response_headers({'Pragma': 'no-cache'})
    @add_response_headers({'Expires': '0'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def headers(f):
    @wraps(f)
    @add_response_headers({'Server': 'dcnws'})
    @add_response_headers({'Cache-Control': 'no-cache, no-store, must-revalidate'})
    @add_response_headers({'Pragma': 'no-cache'})
    @add_response_headers({'Expires': '0'})
    @add_response_headers({'X-Frame-Options': 'SAMEORIGIN'})
    @add_response_headers({'X-XSS-Protection': '1; mode=block'})
    @add_response_headers({'X-Content-Type-Options': 'nosniff'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def api_authenticated(f):
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if app.login_manager._login_disabled:
            return f(*args, **kwargs)
        elif not current_user.is_authenticated:
            syslog.syslog(syslog.LOG_WARNING,
                          "unauthenticated access from: %s" %\
                          request.remote_addr)
            return Response("error", "authenticate")
        return f(*args, **kwargs)
    return decorated_view

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def authenticated(f):
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if app.login_manager._login_disabled:
            return f(*args, **kwargs)
        elif not current_user.is_authenticated:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_view

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def do_get(address, port, uri, secret, timeout=5):
    target = "http://" + address + ":" + str(port) + uri
    headers = {'X-FuzzLabs-Auth': secret}
    try:
        r = requests.get(target, headers=headers, timeout=timeout)
    except Exception, ex:
        syslog.syslog(syslog.LOG_ERR,
                      "failed to request data from engine: %s" % str(ex))
        return None
    if r.status_code != requests.codes.ok: return None
    data = None
    try:
        data = json.loads(r.text)
    except Exception, ex:
        return None
    return data

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine", methods=['GET', 'POST'])
@api_headers
@validate
@api_authenticated
def api_engine():
    if request.method == "GET":
        engines_list = []
        engines = db.session.query(Engine)
        for engine in engines:
            if engine.owner == current_user.username:
                engine.owner = "You (" + current_user.username + ")"

            engines_list.append({
                "id": engine.id,
                "name": engine.name,
                "address": engine.address,
                "port": engine.port,
                "active": engine.active,
                "owner": engine.owner
            })

        r = Response("success", "engines", engines_list).get()
        return make_response(r, 200)

    if request.method == "POST":
        try:
            data = request.get_json()
        except Exception, ex:
            syslog.syslog(syslog.LOG_WARNING,
                          "invalid data from user %s: %s" %\
                          (current_user.username, request.remote_addr))
            r = Response("error", "Invalid data.").get()
            return make_response(r, 400)

    if not data:
        syslog.syslog(syslog.LOG_WARNING,
                      "invalid data from user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Invalid data.").get()
        return make_response(r, 400)

    if not data.get('name') or not data.get('address'):
        syslog.syslog(syslog.LOG_WARNING,
                      "invalid data from user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Invalid data.").get()
        return make_response(r, 400)

    port = 26000
    if data.get('port'):
        port = int(data.get('port'))
    if (port > 65535 or port < 1):
        syslog.syslog(syslog.LOG_WARNING,
                      "invalid data from user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Invalid data.").get()
        return make_response(r, 400)

    if not do_validate("address", data.get('address')) or \
       not do_validate("name", data.get('name')):
        syslog.syslog(syslog.LOG_WARNING,
                      "invalid data from user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Invalid data.").get()
        return make_response(r, 400)

    try:
        engine = Engine(name=data.get('name'),
                        address = data.get('address'),
                        port    = port,
                        secret  = data.get('password'),
                        active  = 1,
                        owner   = current_user.username)
        db.session.add(engine)
        db.session.commit()
    except Exception, ex:
        syslog.syslog(syslog.LOG_WARNING,
                      "failed to add engine, user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Failed to add engine.").get()
        return make_response(r, 400)

    syslog.syslog(syslog.LOG_INFO,
                  "engine successfully registered by user %s: %s" %\
                  (current_user.username, request.remote_addr))
    r = Response("success", "Engine registeration successful.").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/delete", methods=['GET'])
@api_headers
@validate
@api_authenticated
def api_engine_delete(id):
    try:
        engine = db.session.query(Engine).filter_by(id=id).first()
        if engine:
            db.session.delete(engine)
            db.session.commit()
    except Exception, ex:
        syslog.syslog(syslog.LOG_WARNING,
                      "failed to remove engine, user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Failed to remove engine.").get()
        return r

    # If engine removed, delete all related jobs from the database.
    job = db.session.query(Job).filter(
                        Job.engine_id == id
                        ).delete()
    db.session.commit()

    syslog.syslog(syslog.LOG_INFO,
                  "engine sucessfully removed by user %s: %s" %\
                  (current_user.username, request.remote_addr))
    r = Response("success", "Engine removed.").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/activate", methods=['GET'])
@api_headers
@validate
@api_authenticated
def api_engine_activate(id):
    try:
        engine = db.session.query(Engine).filter_by(id=id).first()
        engine.active = 1
        db.session.add(engine)
        db.session.commit()
    except Exception, ex:
        syslog.syslog(syslog.LOG_WARNING,
                      "failed to activate engine, user %s: %s" %\
                      (current_user.username, request.remote_addr))
        r = Response("error", "Failed to activate engine.").get()
        return r
    syslog.syslog(syslog.LOG_INFO,
                  "engine activated by user %s: %s" %\
                  (current_user.username, request.remote_addr))
    r = Response("success", "Engine activated.").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/jobs", methods=['GET'])
@api_headers
@validate
@api_authenticated
def api_engine_jobs():
    jobs = db.session.query(Job).order_by(desc(Job.job_started))

    if jobs.count() == 0:
        r = Response("success", "No jobs available.").get()
        return r

    jobs_list = []
    for job in jobs:
        job_data = {
            "id"          : job.id,
            "job_id"      : job.job_id,
            "name"        : job.name,
            "engine_id"   : job.engine_id,
            "job_loaded"  : job.job_loaded,
            "job_started" : job.job_started,
            "job_stopped" : job.job_stopped,
            "status"      : job.status,
            "c_m_index"   : job.c_m_index,
            "t_m_index"   : job.t_m_index,
            "crashes"     : job.crashes,
            "warnings"    : job.warnings,
            "session"     : json.loads(job.session),
            "target"      : json.loads(job.target),
            "conditions"  : json.loads(job.conditions),
            "agent"       : json.loads(job.agent),
            "requests"    : json.loads(job.requests)
        }

        jobs_list.append(job_data)

    r = Response("success", "jobs", jobs_list).get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/job/<job_id>/delete", methods=['GET'])
@api_headers
@validate
@api_authenticated
def delete_job(id, job_id):
    engine = db.session.query(Engine).filter_by(id=id).first()
    if engine:
        r_data = do_get(engine.address,
                        engine.port,
                        "/jobs/" + job_id + "/delete",
                        engine.secret)
        if not r_data:
            r = Response("error", "Failed to delete job.").get()
            return r
        if not r_data.get('status') or r_data.get('status') == "error":
            r = Response("error", "Failed to delete job.").get()
            return r

    job = db.session.query(Job).filter(
                        (Job.engine_id == id) &\
                        (Job.job_id == job_id)
                        ).first()
    if job:
        db.session.delete(job)
        db.session.commit()

    r = Response("success", "deleted").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/job/<job_id>/pause", methods=['GET'])
@api_headers
@validate
@api_authenticated
def pause_job(id, job_id):
    engine = db.session.query(Engine).filter_by(id=id).first()
    if not engine:
        r = Response("error", "Failed to pause job: engine does not exist.").get()
        return r
    r_data = do_get(engine.address,
                    engine.port,
                    "/jobs/" + job_id + "/pause",
                    engine.secret)
    if not r_data:
        r = Response("error", "Failed to pause job.").get()
        return r
    if not r_data.get('status') or r_data.get('status') == "error":
        r = Response("error", "Failed to pause job.").get()
        return r
    r = Response("success", "paused").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/job/<job_id>/start", methods=['GET'])
@api_headers
@validate
@api_authenticated
def resume_job(id, job_id):
    engine = db.session.query(Engine).filter_by(id=id).first()
    if not engine:
        r = Response("error", "Failed to start job: engine does not exist.").get()
        return r
    r_data = do_get(engine.address,
                    engine.port,
                    "/jobs/" + job_id + "/start",
                    engine.secret)
    if not r_data:
        r = Response("error", "Failed to start job.").get()
        return r
    if not r_data.get('status') or r_data.get('status') == "error":
        r = Response("error", "Failed to start job.").get()
        return r
    r = Response("success", "resumed").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/job/<job_id>/restart", methods=['GET'])
@api_headers
@validate
@api_authenticated
def restart_job(id, job_id):
    engine = db.session.query(Engine).filter_by(id=id).first()
    if not engine:
        r = Response("error", "Failed to restart job: engine does not exist.").get()
        return r
    r_data = do_get(engine.address,
                    engine.port,
                    "/jobs/" + job_id + "/restart",
                    engine.secret)
    if not r_data:
        r = Response("error", "Failed to restart job.").get()
        return r
    if not r_data.get('status') or r_data.get('status') == "error":
        r = Response("error", "Failed to restart job.").get()
        return r
    r = Response("success", "restarted").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/api/engine/<id>/job/<job_id>/stop", methods=['GET'])
@api_headers
@validate
@api_authenticated
def stop_job(id, job_id):
    engine = db.session.query(Engine).filter_by(id=id).first()
    if not engine:
        r = Response("error", "Failed to stop job: engine does not exist.").get()
        return r
    r_data = do_get(engine.address,
                    engine.port,
                    "/jobs/" + job_id + "/stop",
                    engine.secret)
    if not r_data:
        r = Response("error", "Failed to stop job.").get()
        return r
    if not r_data.get('status') or r_data.get('status') == "error":
        r = Response("error", "Failed to stop job.").get()
        return r
    r = Response("success", "stopped").get()
    return r

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/", methods=['GET'])
@headers
@validate
@authenticated
def root():
    return render_template('main.tpl')

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/logout", methods=['GET'])
@headers
@validate
@authenticated
def logout():
    syslog.syslog(syslog.LOG_INFO,
                  "user %s logged out from %s" %\
                  (current_user.username, request.remote_addr))
    logout_user()
    return render_template('login.tpl')

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/login", methods=['GET', 'POST'])
@headers
@validate
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        user = db.session.query(User).filter_by(email=username).first()
        if not user:
            syslog.syslog(syslog.LOG_WARNING,
                          "invalid login request from %s" %\
                          request.remote_addr)
            return render_template('login.tpl')

        if user.is_correct_password(password):
            login_user(user)
            syslog.syslog(syslog.LOG_INFO,
                          "user %s successfully authenticated from %s" %\
                          (username, request.remote_addr))
            return redirect(url_for('root'))

        syslog.syslog(syslog.LOG_WARNING,
                      "authentication failed for user %s: %s" %\
                      (username, request.remote_addr))
        return redirect(url_for('login'))
    else:
        syslog.syslog(syslog.LOG_WARNING,
                      "invalid login request from %s" %\
                      request.remote_addr)
        return render_template('login.tpl')

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/register", methods=['GET', 'POST'])
@headers
@validate
def register():
    if request.method == "POST":
        email = request.form['user_email']
        u_name = request.form['user_name']
        u_password_1 = request.form['user_password_1']
        u_password_2 = request.form['user_password_2']

        if u_password_1 != u_password_2:
            return redirect(url_for('register'))

        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, username=u_name, password=u_password_1)
            db.session.add(user)
            db.session.commit()
            syslog.syslog(syslog.LOG_INFO,
                          "successful registration for user %s: %s" %\
                          (u_name, request.remote_addr))
            return redirect(url_for('login'))
        else:
            syslog.syslog(syslog.LOG_WARNING,
                          "registration failed with username %s: %s" %\
                          (u_name, request.remote_addr))
            return redirect(url_for('register'))
    else:
        return render_template('register.tpl')

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.route("/<path:filename>", methods=['GET'])
@headers
@validate
def base_static(filename):
    return send_from_directory(app.root_path + '/static/', filename)

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

@app.errorhandler(404)
@headers
def server_error(e):
    return redirect(url_for("root"))

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

"""
@app.errorhandler(500)
@headers
def server_error(e):
    return redirect(url_for("root"))
"""

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    syslog.syslog(syslog.LOG_INFO, 'FuzzLabs webserver is accepting data')
    context = (app.root_path + '/etc/ssl/server.crt',
               app.root_path + '/etc/ssl/server.key')
    app.run(host="0.0.0.0", port=443, debug=True, ssl_context=context,
            threaded=True)

