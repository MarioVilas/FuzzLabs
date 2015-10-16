import json
import time
import syslog
import requests
import threading
import Queue
from Queue import Queue

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class EngineThread(threading.Thread):

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, thread_queue, root, config, data_queue, engine):
        threading.Thread.__init__(self)
        self.root         = root
        self.config       = config
        self.dqueue       = data_queue
        self.engine       = engine
        self.thread_queue = thread_queue
        self.running      = True
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def do_get(self, address, port, uri, secret, timeout=5):
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

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def enqueue(self, item):
        try:
            self.dqueue.put(item, True, 1)
        except Queue.Full:
            self.enqueue(item)
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to process job: %s" % str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def engine_offline(self):
        syslog.syslog(syslog.LOG_ERR,
                      "engine %s offline, disabling" % self.engine.name)
        self.enqueue({
            "item":   "engine",
            "action": "disable",
            "data":   self.engine
        })

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def process_jobs(self):
        d = self.do_get(self.engine.address,
                        self.engine.port,
                        "/jobs",
                        self.engine.secret,
                        3)

        if d == None or d.get('status') == None or d.get('status') == "error":
            self.engine_offline()
            return False
        if not d.get('data'): return True

        self.enqueue({
            "item":   "job",
            "action": "handle",
            "active": 1,
            "engine": self.engine,
            "data":   d.get('data')
        })

        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def process_issues(self):
        d = self.do_get(self.engine.address,
                        self.engine.port,
                        "/issues",
                        self.engine.secret,
                        3)

        if d == None or d.get('status') == None or d.get('status') == "error":
            self.engine_offline()
            return False
        if not d.get('data'): return True

        issues = d.get('data')

        for issue in issues:
            if not issue.get('id'): continue
            i = self.do_get(self.engine.address,
                            self.engine.port,
                            "/issues/" + str(issue.get('id')),
                            self.engine.secret,
                            3)
            if i == None or i.get('status') == None or \
               i.get('status') == "error" or not i.get('data'):
                self.engine_offline()
                return False

            self.enqueue({
                "item":   "issue",
                "action": "handle",
                "engine": self.engine,
                "data":   i.get('data')
            })

            i = self.do_get(self.engine.address,
                            self.engine.port,
                            "/issues/" + str(issue.get('id')) + "/delete",
                            self.engine.secret,
                            3)


    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def stop(self):
        self.running = False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def clear_thread_queue(self):
        """
        Removes the thread from the thread queue. This only happens if the
        engine is no longer available. As in such case the engine will be 
        marked as inactive in the database the service will not fire a new
        engine thread for it.
        Removing the thread from the thread queue allows the service to
        fire up a new engine thread if the users sets the engine online.
        """

        to_remove = None
        for t in self.thread_queue:
            if t["engine"].address == self.engine.address:
                to_remove = t
        if to_remove:
            self.thread_queue.remove(to_remove)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs engine thread is running')

        while self.running:
            if not self.process_jobs():    self.running = False
            if not self.process_issues():  self.running = False
            time.sleep(self.config["general"]["data_collect_interval"])

        self.clear_thread_queue()
        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs engine thread has stopped')

