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
        self.database.log("info", "all workers stopped")

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
            self.database.log("error",
                              "failed to load job data for job %s" % job_id,
                              str(ex))
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
            self.database.log("error", 
                              "failed to lock job %s" % job_id,
                              str(ex))
            return False

        if not self.database.insertJob(job_data):
            self.database.log("error",
                              "failed to save job data for job %s" % job_id,
                              str(ex))
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
                    self.database.log("debug",
                                      "sending to worker %s, cmd: %s, data: %s"
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

        self.database.log("info", "queue listener started")
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
                    self.database.log("error",
                                      "failed to execute queue handler '%s'" %\
                                      cmd["command"],
                                      str(ex))
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
            self.database.log("error",
                              "failed to stop worker %s" % str(worker),
                              str(ex))

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

        self.database.log("info", "initializing worker: %s" % worker["id"])

        worker["job_id"]   = job_id
        worker["c_queue"]  = multiprocessing.Queue()
        worker["p_queue"]  = multiprocessing.Queue()

        job_data = None

        try:
            job_data = self.database.loadJob(job_id)
            if not job_data:
                self.database.log("error",
                                  "failed to load data for job %s" % job_id,
                                  str(ex))
        except Exception, ex:
            self.database.log("error",
                              "error loading data for job %s" % job_id,
                              str(ex))
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
            self.database.log("error",
                              "failed to initialize worker for job %s" %\
                              job_id,
                              str(ex))
            return False

        try:
            worker["process"] = Process(target=worker["instance"].run)
            worker["process"].start()
        except Exception, ex:
            self.database.log("error",
                              "failed to start job %s" % job_id,
                              str(ex))
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

        self.database.log("info",
                          "job delete request received for job %s" %\
                          str(data))

        self.broadcast("job_delete", data)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def e_handle_job_restart(self, sender, data):

        self.database.log("info",
                          "job restart request received for job %s" %\
                          str(data))

        if not self.database.deleteSession(data):
            self.database.log("error",
                              "failed to delete session for job: %s" %\
                              str(data))
            return False

        self.e_handle_job_start(sender, data)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def e_handle_job_stop(self, sender, data):

        self.database.log("info",
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

        self.database.log("info",
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
            self.database.log("info",
                              "starting job %s" % str(data))
            self.start_worker(data)
        else:
            self.database.log("info",
                              "resuming job %s" % str(data))
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
        self.database.log("info", "job handler started")

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
                self.database.log("error", 
                                  "failed to process jobs",
                                  str(ex))

            time.sleep(2)

        self.database.log("info", "job handler stopped")

