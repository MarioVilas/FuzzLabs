import re
import os
import json
import time
import syslog
import psutil
import threading
from functools import wraps
from OpenSSL import SSL
from flask import request
from flask import make_response
from flask import Flask, make_response
from pydispatch import dispatcher
from classes import Event as ev
from classes import DatabaseHandler as db

__version__ = "2.1.0"

database = None
fuzzlabs_root = None

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

whitelist = {}
whitelist["id"]       = '^[0-9]*$'
whitelist["job_id"]   = '^[a-f0-9]{32}$'
whitelist["datetime"] = '^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}$'

# =============================================================================
#
# =============================================================================

class system_stats:

    def __init__(self):
        pass

    def get_cpu_stats(self):
        cpu_used = int(round((psutil.cpu_times().user * 100) + \
                   (psutil.cpu_times().system * 100), 0))
        cpu_free = int(round(psutil.cpu_times().idle * 100, 0))

        cpu_stat = {
            "used": cpu_used,
            "free": cpu_free
        }

        return cpu_stat

    def get_memory_stats(self):

        memory = {
            "physical": {
                "used": psutil.phymem_usage().used,
                "free": psutil.phymem_usage().free
            },
            "virtual": {
                "used": psutil.virtmem_usage().used,
                "free": psutil.virtmem_usage().free
            }
        }

        return memory

    def get_disk_stats(self):

        disk_stat = {
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free
        }

        return disk_stat

    def get_stats_summary(self):

        summary = {
            "cpu": self.get_cpu_stats(),
            "disk": self.get_disk_stats(),
            "memory": self.get_memory_stats()
        }

        return summary

# =============================================================================
#
# =============================================================================

class archives_collector(threading.Thread):

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, config):
        threading.Thread.__init__(self)
        self.config = config

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def handle_rsp_archives_list(self, sender, data = ""):
        global archives_status
        archives_status = data

        if self.config['general']['debug'] >= 1:
            syslog.syslog(syslog.LOG_INFO, "archives received: %s" %
                          str(archives_status))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def get(self):
        global archives_status
        return archives_status

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        syslog.syslog(syslog.LOG_INFO, "archives status collector started")
        dispatcher.connect(self.handle_rsp_archives_list,
                           signal=ev.Event.EVENT__RSP_ARCHIVES_LIST,
                           sender=dispatcher.Any)
        while True:
            try:
                dispatcher.send(signal=ev.Event.EVENT__REQ_ARCHIVES_LIST,
                                sender="WEBSERVER")
            except Exception, ex:
                syslog.syslog(syslog.LOG_ERR,
                              "failed to send archives request event (%s)" %
                              str(ex))
            time.sleep(5)

# =============================================================================
#
# =============================================================================

class jobs_status_collector(threading.Thread):

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, config):
        threading.Thread.__init__(self)
        self.config = config

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def handle_rsp_jobs_list(self, sender, data = ""):
        global jobs_status
        jobs_status = data

        if self.config['general']['debug'] >= 1:
            syslog.syslog(syslog.LOG_INFO, "jobs status received: %s" %
                          str(jobs_status))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def get(self):
        global jobs_status
        return jobs_status

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        syslog.syslog(syslog.LOG_INFO, "jobs status collector started")
        dispatcher.connect(self.handle_rsp_jobs_list,
                           signal=ev.Event.EVENT__RSP_JOBS_LIST,
                           sender=dispatcher.Any)
        while True:
            try:
                dispatcher.send(signal=ev.Event.EVENT__REQ_JOBS_LIST,
                                sender="WEBSERVER")
            except Exception, ex:
                syslog.syslog(syslog.LOG_ERR,
                              "failed to send job list request event (%s)" %
                              str(ex))
            time.sleep(3)

# =============================================================================
#
# =============================================================================

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
                    r = Response("error", "invalid data").get()
                    return make_response(r, 400)
        url_params = request.args.items()
        if len(url_params) > 0:
            for key, value in url_params:
                if key not in whitelist: continue
                if not do_validate(key, value):
                    r = Response("error", "invalid data").get()
                    return make_response(r, 400)
        if request.method == "POST":
            # Not checking data in JSON here just if the JSON is valid.
            try:
                data = request.get_json()
            except Exception, ex:
                r = Response("error", "invalid data").get()
                return make_response(r, 400)
        return f(**kwargs)
    return validate_input

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def add_response_headers(headers={}):
    """This decorator adds the headers passed in to the response"""
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

def apiheaders(f):
    @wraps(f)
    @add_response_headers({'Server': 'dcnws'})
    @add_response_headers({'Content-Type': 'application/json'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def is_job_archived(job_id):
    global fuzzlabs_root
    a_dir = fuzzlabs_root + "/jobs/archived/" + job_id

    if os.path.exists(a_dir):
        return True
    return False

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

def is_job_queued(job_id):
    global fuzzlabs_root
    q_dir = fuzzlabs_root + "/jobs/queue/" + job_id

    if os.path.exists(q_dir):
        return True
    return False

# =============================================================================
#
# =============================================================================

class webserver(threading.Thread):

    app = Flask(__name__)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def descriptor(self):
        return(dict([
            ('type', 'module'),
            ('version', __version__),
            ('name', 'webserver')
        ]))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, root, config):
        threading.Thread.__init__(self)
        global database
        global fuzzlabs_root
        self.root = fuzzlabs_root = root
        self.config = config
        self.setDaemon(True)
        self.running = True
        self.server = None
        self.jobs_collector = None
        self.archives_collector = None

        database = db.DatabaseHandler(self.config, 
                                      self.root)

        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

        if self.config == None:
            syslog.syslog(syslog.LOG_ERR, 'invalid configuration')
            self.running = False
        else:
            self.setDaemon(True)
            self.running = True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def is_running(self):
        return self.running

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def stop(self):
        self.running = False
        syslog.syslog(syslog.LOG_INFO, 'webserver stopped')

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/", methods=['GET'])
    @apiheaders
    @validate
    def root():
        return json.dumps({})

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_queue():
        global jobs_status
        r = Response("success", "jobs", json.loads(jobs_status)).get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs/archive", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_archive():
        global archives_status
        r = Response("success", "jobs", json.loads(archives_status)).get()
        return r


    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs/<job_id>/stop", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_delete(job_id):
        syslog.syslog(syslog.LOG_INFO,
                      "stop request received for job: %s" % job_id)
        dispatcher.send(signal=ev.Event.EVENT__REQ_JOB_DELETE,
                        sender="WEBSERVER",
                        data=job_id)
        r = Response("success", "stopped").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs/<job_id>/delete", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_trash(job_id):
        syslog.syslog(syslog.LOG_INFO,
                      "delete request received for job: %s" % job_id)
        dispatcher.send(signal=ev.Event.EVENT__REQ_ARCHIVES_DELETE,
                        sender="WEBSERVER",
                        data=job_id)
        r = Response("success", "deleted").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs/<job_id>/restart", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_restart(job_id):
        syslog.syslog(syslog.LOG_INFO,
                      "restart request received for job: %s" % job_id)
        dispatcher.send(signal=ev.Event.EVENT__REQ_ARCHIVES_RESTART,
                        sender="WEBSERVER",
                        data=job_id)
        r = Response("success", "restarted").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs/<job_id>/pause", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_pause(job_id):
        syslog.syslog(syslog.LOG_INFO,
                      "pause request received for job: %s" % job_id)
        dispatcher.send(signal=ev.Event.EVENT__REQ_JOB_PAUSE, 
                        sender="WEBSERVER", 
                        data=job_id)
        r = Response("success", "paused").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/jobs/<job_id>/start", methods=['GET'])
    @apiheaders
    @validate
    def r_jobs_start(job_id):

        syslog.syslog(syslog.LOG_INFO,
                      "start request received for job: %s" % job_id)

        if is_job_archived(job_id):
            syslog.syslog(syslog.LOG_INFO,
                          "starting archived job: %s" % job_id)
            dispatcher.send(signal=ev.Event.EVENT__REQ_ARCHIVES_START,
                            sender="WEBSERVER",
                            data=job_id)
        else:
            syslog.syslog(syslog.LOG_INFO,
                          "resuming job: %s" % job_id)
            dispatcher.send(signal=ev.Event.EVENT__REQ_JOB_RESUME,
                            sender="WEBSERVER",
                            data=job_id)

        r = Response("success", "started").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/issues", methods=['GET'])
    @apiheaders
    @validate
    def r_get_issues():
        global database
        issues = []
        try:
            issues = database.loadIssues()
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to retrieve issues: %s" % str(ex))
            r = Response("error", "issues").get()
            return r
        r = Response("success", "issues", issues).get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/issues/<id>", methods=['GET'])
    @apiheaders
    @validate
    def r_get_issue_by_id(id):
        global database
        issue = None
        try:
            issue = database.loadIssue(id)
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to retrieve issue: %s" % str(ex))
            r = Response("error", "issues").get()
            return r
        r = Response("success", "issue", database.loadIssue(id)).get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/issues/<id>/delete", methods=['GET'])
    @apiheaders
    @validate
    def r_delete_issue_by_id(id):
        global database
        syslog.syslog(syslog.LOG_INFO,
                      "delete request received for issue: %s" % id)
        try:
            database.deleteIssue(id)
        except Exception, ex:
            r = Response("error", "delete").get()
            return r
        r = Response("success", "deleted").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/engine/shutdown", methods=['GET'])
    @apiheaders
    @validate
    def r_engine_shutdown():
        # TBD
        r = Response("error", "not supported").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/engine/status", methods=['GET'])
    @apiheaders
    @validate
    def r_engine_status():
        # TBD
        r = Response("error", "not supported").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/engine/logs", methods=['GET'])
    @apiheaders
    @validate
    def r_engine_logs():
        # TBD
        r = Response("error", "not supported").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route("/engine/logs/<datetime>", methods=['GET'])
    @apiheaders
    @validate
    def r_engine_logs_from(datetime):
        # TBD
        r = Response("error", "not supported").get()
        return r

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    @apiheaders
    def catch_all(path):
        r = Response("error", "invalid data").get()
        return make_response(r, 400)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        try:
            self.jobs_collector = jobs_status_collector(self.config)
            self.jobs_collector.start()
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          'failed to start job status collector (%s)' %
                          str(ex))

        try:
            self.archives_collector = archives_collector(self.config)
            self.archives_collector.start()
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          'failed to start archives collector (%s)' % str(ex))

        syslog.syslog(syslog.LOG_INFO, 'webserver thread is accepting data')
        self.app.run(host=self.config['api']['listen_address'],
                     port=self.config['api']['listen_port'],
                     debug=False)

