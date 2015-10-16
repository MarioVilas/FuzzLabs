"""
Module to handle jobs.
"""

import os
import re
import sys
import json
import copy
import time
import Queue
import shutil
import random
import syslog
import signal
import inspect
import hashlib
import threading
import multiprocessing
from threading import Thread
from pydispatch import dispatcher
from multiprocessing import Process

from jobworker import jobworker
from classes import Event as ev
from classes import DatabaseHandler as dh

__version__    = "2.1.0"

# =============================================================================
#
# =============================================================================

class jobshandler(threading.Thread):

    def descriptor(self):
        return(dict([
            ('type', 'module'),
            ('version', __version__),
            ('name', 'jobshandler')
        ]))

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def __init__(self, root, config):
        """
        Initialize the module.

        @type  root:     String
        @param root:     Full path to the FuzzLabs root directory
        @type  config:   Dictionary
        @param config:   The complete configuration as a dictionary
        """

        threading.Thread.__init__(self)
        self.root              = root
        self.config            = config
        self.running           = False
        self.jobs_dir          = self.root + "/jobs" 
        self.id                = self.generate_id()
        self.database          = dh.DatabaseHandler(self.config, self.root)
        self.workers           = []

        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def generate_id(self):
        """
        Generate random IDs to be used to identify the job handler and the
        worker processes.

        @rtype:          String
        @return:         Generated random ID
        """

        h_in = str(random.getrandbits(64))
        h_in = str(time.time())
        return hashlib.sha1(h_in).hexdigest()

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def is_running(self):
        """
        Return job handler status.
        """

        return self.running

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def stop(self):
        """
        Stop the job handler module. As part of the shutdown procedure all
        workers will be stopped.

        for worker in self.workers:
            self.delete_worker(worker["id"])

        self.workers = []
        syslog.syslog(syslog.LOG_INFO, "all workers stopped")
        """

        self.running = False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def process_job(self, job_id, filename):
        job_file = self.jobs_dir + "/" + filename

        try:
            job_data = json.load(open(job_file, 'r'))
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to load job data for job %s (%s)" %\
                          (job_id, str(ex)))
            return False

        job_data["job_id"]      = hashlib.md5(json.dumps(job_data)).hexdigest()
        job_data["node"]        = ''
        job_data["status"]      = 0
        job_data["c_m_index"]   = 0 
        job_data["t_m_index"]   = 0
        job_data["crashes"]     = 0
        job_data["warnings"]    = 0
        job_data["job_loaded"]  = time.time()
        job_data["job_started"] = 0
        job_data["job_stopped"] = 0


        job_lock = job_file.split(".")
        job_lock[len(job_lock) - 1] = "jlock"
        job_lock = ".".join(job_lock)

        try:
            shutil.move(job_file, job_lock)
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to lock job %s (%s)" %\
                          (job_id, str(ex)))
            return False

        if not self.database.insertJob(job_data):
            syslog.syslog(syslog.LOG_ERR,
                          "failed to save job data for job %s (%s)" %\
                          (job_id, str(ex)))
            return False

        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def broadcast(self, command, data = None, excluded_workers = []):
        """
        Broadcast a message to all workers via the queues.

        @type  command:              String
        @param command:              The command to be broadcasted
        @type  data:                 String
        @param data:                 The data belonging to the command
        @type  excluded_workers:     List
        @param excluded_workers:     List of workers to be excluded from the
                                     broadcast
        """

        for worker in self.workers:
            if worker in excluded_workers: continue
            self.send_to(worker["id"], command, data)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def send_to(self, worker_id, command, data):
        """
        Send a message to a worker identified by its ID via the associated
        queue.

        @type  worker_id:  String
        @param worker_id:  The ID of the worker the message has to be sent to
        @type  command:    String
        @param command:    The command to be broadcasted
        @type  data:       String
        @param data:       The data belonging to the command
        """

        for worker in self.workers:
            if worker_id == worker["id"]:
                if self.config["general"]["debug"] > 4:
                    syslog.syslog(syslog.LOG_INFO,
                                  "sending to worker %s, cmd: %s, data: %s" %\
                                  (worker["id"], command, str(data)))

                worker["c_queue"].put({
                    "from": self.id,
                    "to": worker["id"],
                    "command": command,
                    "data": data
                })

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def check_jobs(self):
        for dirpath, dirnames, filenames in os.walk(self.jobs_dir):
            for filename in filenames:
                f = filename.split(".")
                if len(f) < 2: continue
                if f[1] != "job": continue
                self.process_job(f[0], filename)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def listener(self):
        """
        Check every queue assigned to workers to see if there is a message
        sent by a worker waiting to be processed.
        """

        syslog.syslog(syslog.LOG_INFO, "queue listener started")
        while self.running:
            for worker in self.workers:
                cmd = None
                try:
                    cmd = worker["p_queue"].get_nowait()
                except Queue.Empty:
                    pass
                if not cmd: continue

                try:
                    getattr(self, 'q_handle_' + cmd["command"], None)(cmd)
                except Exception, ex:
                    syslog.syslog(syslog.LOG_ERR,
                                  "failed to execute queue handler '%s' (%s)" %\
                                  (cmd["command"], str(ex)))

            time.sleep(1)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def delete_worker(self, worker_id):
        """
        Delete a worker. The worker is stopped then all references to it is
        deleted.

        @type  worker_id:   String
        @param worker_id:   The ID of the worker process
        """

        w_remove = None
        s_remove = None

        for worker in self.workers:
            if worker["id"] == worker_id:
                w_remove = worker

        if not w_remove: return

        self.workers.remove(w_remove)
        w_remove["c_queue"].put({
                    "from": self.id,
                    "to": worker["id"],
                    "command": "shutdown"
            })

        w_remove["c_queue"].close()
        w_remove["c_queue"].join_thread()

        try:
            w_remove["process"].join()
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR, "failed to stop worker %s (%s)" %
                          (worker, str(ex)))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def start_worker(self, job_id):
        """
        Spawn a worker process to executed the job identified by job_id.

        @type  job_id:   String
        @param job_id:   The ID of the job to be executed

        @rtype:          Dictionary
        @return:         Dictionary with details related to the worker
        """

        worker = {}
        worker["id"]       = self.generate_id()

        syslog.syslog(syslog.LOG_INFO,
                      "initializing worker %s ..." % worker["id"])

        worker["job_id"]   = job_id
        worker["c_queue"]  = multiprocessing.Queue()
        worker["p_queue"]  = multiprocessing.Queue()

        job_data = None

        try:
            job_data = self.database.loadJob(job_id)
            if not job_data:
                syslog.syslog(syslog.LOG_ERR,
                              "failed to load data for job %s" %\
                              job_id)
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "error loading data for job %s (%s)" %\
                          (job_id, str(ex)))
            return False

        try:
            worker["instance"] = jobworker(self.id,
                                           worker["id"],
                                           job_id,
                                           worker["c_queue"],
                                           worker["p_queue"],
                                           self.root,
                                           self.config,
                                           job_data)
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to initialize worker for job %s (%s)" %\
                          (job_id, str(ex)))
            return False

        try:
            worker["process"] = Process(target=worker["instance"].run)
            worker["process"].start()
        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to start job %s (%s)" %\
                          (job_id, str(ex)))
            return False

        self.workers.append(worker)
        return worker

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def q_handle_job_finished(self, cmd):
        """
        When a worker finished executing a job it sends a job finished message
        on the queue associated with the worker. This handler listens for such
        messages and removes finished jobs from the list of registered jobs
        kept to maintain state information.

        @type  cmd:      Dictionary
        @param cmd:      A dictionary containing the ID of the finished job
        """

        job_id = cmd["data"]
        self.delete_worker(cmd["from"])

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def e_handle_job_delete(self, sender, data):
        """
        Handle job delete request events sent by the web server. The requested
        job will get deleted.

        @type  sender:   String
        @param sender:   The string identifying the sender of the event
        @type  data:     String
        @param data:     The ID of the job to be deleted
        """

        syslog.syslog(syslog.LOG_INFO,
                      "job delete request received for job %s" %\
                      str(data))

        self.broadcast("job_delete", data)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def e_handle_job_restart(self, sender, data):

        syslog.syslog(syslog.LOG_INFO,
                      "job restart request received for job %s" %\
                      str(data))

        if not self.database.deleteSession(data):
            syslog.syslog(syslog.LOG_ERR,
                          "failed to delete session data for job %s" +\
                          ", cannot restart job" %\
                          data)
            return False

        self.e_handle_job_start(sender, data)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def e_handle_job_stop(self, sender, data):

        syslog.syslog(syslog.LOG_INFO,
                      "job stop request received for job %s" %\
                      str(data))

        self.broadcast("job_stop", data)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def e_handle_job_pause(self, sender, data):
        """
        Handle job pause request events sent by the web server. The requested
        job will get paused.

        @type  sender:   String
        @param sender:   The string identifying the sender of the event
        @type  data:     String
        @param data:     The ID of the job to be paused
        """

        syslog.syslog(syslog.LOG_INFO,
                      "job pause request received for job %s" %\
                      str(data))

        self.broadcast("job_pause", data)

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def e_handle_job_start(self, sender, data):
        """
        Handle job resume request events sent by the web server. The requested
        job will get resumed.

        @type  sender:   String
        @param sender:   The string identifying the sender of the event
        @type  data:     String
        @param data:     The ID of the job to be resumed
        """

        new = True
        for worker in self.workers:
            if worker["job_id"] == data:
                new = False

        if new:
            syslog.syslog(syslog.LOG_INFO,
                          "starting job %s" %\
                          str(data))
            self.start_worker(data)
        else:
            syslog.syslog(syslog.LOG_INFO,
                          "resuming job %s" %\
                          str(data))
            self.broadcast("job_resume", data)
        return True

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def run(self):
        """
        The main method of the job handler module.
        """

        self.running = True
        syslog.syslog(syslog.LOG_INFO, "job handler started")

        l = threading.Thread(target=self.listener)
        l.start()

        dispatcher.connect(self.e_handle_job_start,
                           signal=ev.Event.EVENT__REQ_JOB_START,
                           sender=dispatcher.Any)
        dispatcher.connect(self.e_handle_job_pause,
                           signal=ev.Event.EVENT__REQ_JOB_PAUSE,
                           sender=dispatcher.Any)
        dispatcher.connect(self.e_handle_job_stop,
                           signal=ev.Event.EVENT__REQ_JOB_STOP,
                           sender=dispatcher.Any)
        dispatcher.connect(self.e_handle_job_restart,
                           signal=ev.Event.EVENT__REQ_JOB_RESTART,
                           sender=dispatcher.Any)
        dispatcher.connect(self.e_handle_job_delete,
                           signal=ev.Event.EVENT__REQ_JOB_DELETE,
                           sender=dispatcher.Any)

        while self.running:
            try:
                self.check_jobs()
            except Exception, ex:
                syslog.syslog(syslog.LOG_ERR,
                              "failed to process jobs (%s)" %\
                              str(ex))

            time.sleep(2)

        syslog.syslog(syslog.LOG_INFO, "job handler stopped")

