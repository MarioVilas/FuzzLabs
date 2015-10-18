"""
Job worker implementation.
"""

import os
import sys
import json
import time
import Queue
import shutil
import threading
import multiprocessing
from threading import Thread
from sulley import *

from classes import DatabaseHandler as dh

# =============================================================================
#
# =============================================================================

class jobworker():

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def __init__(self, parent, id, job_id, c_queue, p_queue, root, config, job):
        """
        Initialize the worker

        @type  parent:   String
        @param parent:   The ID of the parent
        @type  id:       String
        @param id:       The ID of the worker
        @type  c_queue:  multiprocessing.Queue
        @param c_queue:  The queue the client receives messages on
        @type  p_queue:  multiprocessing.Queue
        @param p_queue:  The queue used to send messages to the parent
        @type  root:     String
        @param root:     The root directory of FuzzLabs
        @type  config:   Dictionary
        @param config:   A dictionary containing the FuzzLabs configuration
        """

        self.root              = root
        self.parent            = parent
        self.id                = id
        self.c_queue           = c_queue
        self.p_queue           = p_queue
        self.config            = config
        self.running           = False
        self.core              = None
        self.job_data          = job

        self.job_id            = job_id
        self.job_status        = {}

        self.database          = dh.DatabaseHandler(self.config, self.root)

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def q_handle_shutdown(self, cmd):
        """
        Handle worker shutdown request sent by the parent. The "cmd" argument
        is not used.
        """

        self.database.log("info",
                          "worker %s received shutdown request received" %\
                          self.id)
        self.core.terminate()

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def q_handle_job_pause(self, cmd):
        """
        Pause the job as requested by the parent.

        @type  cmd:      Dictionary
        @param cmd:      The job pause message as a dictionary
        """

        if cmd["data"] == self.job_id:
            self.core.set_pause()

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def q_handle_job_resume(self, cmd):
        """
        Resume the job as requested by the parent.

        @type  cmd:      Dictionary
        @param cmd:      The job resume message as a dictionary
        """

        if cmd["data"] == self.job_id:
            self.core.set_resume()

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def q_handle_job_delete(self, cmd):
        """
        Delete the job as requested by the parent.

        @type  cmd:      Dictionary
        @param cmd:      The job delete message as a dictionary
        """

        if not self.running: return
        if cmd["data"] == self.job_id:
            self.core.terminate()

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def q_handle_job_stop(self, cmd):
        """
        Stop the job as requested by the parent.

        @type  cmd:      Dictionary
        @param cmd:      The job stop message as a dictionary
        """

        if not self.running: return
        if cmd["data"] == self.job_id:
            self.core.terminate()

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def handle(self, cmd):
        """
        Handle the received message. The handler function is dynamically
        looked up and called, this way handling of new commands can be easily
        implemented by just adding a handler function.

        @type  cmd:      Dictionary
        @param cmd:      The message as a dictionary.
        """

        if not self.validate_queue_message(cmd): return
        try:
            if not self.core: return
            getattr(self, 'q_handle_' + cmd["command"], None)(cmd)
        except Exception, ex:
            self.database.log("error",
                              "worker %s failed to execute queue handler '%s'" %\
                              (self.id, cmd["command"]), 
                              str(ex))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def validate_queue_message(self, message):
        """
        Perform basic validation of a message received via the queue.

        @type  message:  Dictionary
        @param message:  The message as a dictionary
        """

        if not message.has_key("from"): return False
        if not message.has_key("to"): return False
        if not message.has_key("command"): return False
        if message["to"] != self.id: return False
        if message["from"] != self.parent: return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def report_finished(self):
        """
        Report to the parent that the job has been finished.
        """

        self.p_queue.put({
                          "to": self.parent,
                          "from": self.id,
                          "command": "job_finished",
                          "data": self.job_id
                         })

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def stop_worker(self):
        """
        Shut down the worker process.
        """

        try:
            self.report_finished()
        except Exception, ex:
            pass

        try:
            # Remove everything from the queue
            while not self.c_queue.empty(): self.c_queue.get()
        except Exception, ex:
            pass

        try:
            self.p_queue.close()
            self.p_queue.join_thread()
        except Exception, ex:
            pass

        self.database.log("info", "w[%s] terminated" % self.id)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __import_request_file(self):
        """
        Load the protocol/file descriptor.
        """

        r_folder = self.root + "/requests"
        if r_folder not in sys.path: sys.path.insert(0, r_folder)
        global descriptor
        request_file = self.job_data['request']['request_file']
        descriptor = __import__(request_file)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def load_callbacks(self, f_name = None):
        global descriptor
        if not f_name: return None
        try:
            f_name = getattr(descriptor, f_name)
        except Exception, ex:
            self.database.log("error",
                              "worker %s failed to load pre_send function for job %s" %\
                              (self.id, self.job_id), 
                              str(ex))
            f_name = None
        return f_name

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def setup_core(self):
        """
        Set up the fuzzing core.

        @rtype:          Boolean
        @return:         True if success, otherwise False
        """

        try:
            self.__import_request_file()
        except Exception, ex:
            self.database.log("error",
                              "worker %s failed to load descriptor for job %s" %\
                              (self.id, self.job_id), 
                              str(ex))
            return False

        settings   = self.job_data['session']
        agent      = self.job_data.get('agent')
        transport  = self.job_data['target']['transport']
        endpoint   = self.job_data['target']['endpoint']
        conditions = self.job_data['conditions']
        pre_send   = self.job_data['request'].get('pre_send')
        post_send  = self.job_data['request'].get('post_send')

        try:
            self.core = sessions.session(self.config, 
                                 self.root,
                                 self.job_id,
                                 settings,
                                 transport,
                                 conditions,
                                 self.job_data)
            self.core.add_target(endpoint)

            if agent and agent != {}:
                rc = self.core.add_agent(agent)
                if (rc == False):
                    self.database.log("error",
                                      "worker %s failed to set up agent for job %s" %\
                                      (self.id, self.job_id))
                    return False
        except Exception, ex:
            self.database.log("error",
                              "worker %s failed to initialize job %s" %\
                              (self.id, self.job_id), 
                              str(ex))
            return False

        pre_send = self.load_callbacks(pre_send)
        post_send = self.load_callbacks(post_send)

        self.core.set_pre_send(pre_send)
        self.core.set_post_send(post_send)

        try:
            for path in self.job_data['request']['graph']:
                n_c = path.get('current')
                if n_c != None: n_c = s_get(n_c)
                n_n = path.get('next')
                if n_n != None: n_n = s_get(n_n)
                callback = self.load_callbacks(path.get('callback'))
                self.core.connect(n_c, n_n, callback)

        except Exception, ex:
            self.database.log("error",
                              "worker %s failed to process graph for job %s" %\
                              (self.id, self.job_id), 
                              str(ex))
            return False

        return True

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def start_fuzzing(self):
        """
        Start the fuzzing.
        """

        if not self.core: return
        try:
            self.core.fuzz()
            self.running = False
        except Exception, ex:
            self.database.log("error",
                              "worker %s failed to execute job %s" %\
                              (self.id, self.job_id), 
                              str(ex))
            self.running = False
            return

        try:
            self.job_status = self.core.get_status()
        except Exception, ex:
            pass

        self.database.log("info",
                          "worker %s finished job %s" %\
                          (self.id, self.job_id))

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def listener(self):
        """
        Listen for messages on the queue.
        """

        while self.running:
            try: self.handle(self.c_queue.get_nowait())
            except Exception, ex: pass

    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------

    def run(self):
        """
        Main function of the worker.
        """

        self.running = True
        self.database.log("info",
                          "worker %s started, pid: %d" %\
                          (self.id, os.getpid()))
        l = threading.Thread(target=self.listener)
        l.start()

        self.database.log("info",
                          "worker %s executing job %s" %\
                          (self.id, self.job_id))

        if self.setup_core(): self.start_fuzzing()

        self.stop_worker()

