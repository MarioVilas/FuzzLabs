import os
import time
import signal
import syslog
import threading
from Queue import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text
# from sqlalchemy.ext.hybrid import hybrid_property
# from sqlalchemy.orm import relationship, backref
from classes import DatabaseThread as dt
from classes import EngineThread as et

from classes.database.Base import Base
from classes.database.Engine import Engine

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class CollectorDaemon():

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, root, config):
        """
        Initialize daemon.

        @type  root:     String
        @param root:     Full path to the root directory
        @type  config:   Dictionary
        @param config:   The complete configuration as a dictionary
        """

        self.root            = root
        self.config          = config
        self.modules         = None
        self.thread_queue    = []
        self.stdin_path      = self.config['daemon']['stdin']
        self.stdout_path     = self.config['daemon']['stdout']
        self.stderr_path     = self.config['daemon']['stderr']
        self.pidfile_path    = self.config['daemon']['pidfile']
        self.pidfile_timeout = self.config['daemon']['pidfile_timeout']
        self.running         = True
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __sigterm_handler(self, signum, frame):
        """
        Handle SIGTERM signal and abort execution.
        """

        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector is stopping')
        for r_thread in self.thread_queue:
            syslog.syslog(syslog.LOG_INFO, 'collector: stopping engine handler thread')
            r_thread["instance"].stop()
        self.running = False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def has_thread(self, engine):
        for t in self.thread_queue:
            if t["engine"].address == engine.address:
                return True
        return False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def handle_deleted_engines(self, engines):
        to_stop = []
        for r_engine in self.thread_queue:
            still_exists = False
            for c_engine in engines:
                if r_engine["engine"].address == c_engine.address and \
                   r_engine["engine"].port == c_engine.port and \
                   r_engine["engine"].id == c_engine.id:
                       still_exists = True
                       break
            if not still_exists:
                to_stop.append(r_engine)

        for t_engine in to_stop:
            t_engine["instance"].stop()
            self.thread_queue.remove(t_engine)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        os.setsid()
        os.umask(077)
        signal.signal(signal.SIGTERM, self.__sigterm_handler)

        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector is running')

        db_engine = None
        db = None
        try:
            db_engine = create_engine('sqlite:///' + self.root +\
                                   '/etc/webserver.db', echo=False)
            Session = sessionmaker(bind = db_engine)
            db = Session()
            Base.metadata.create_all(db_engine)
            db.commit()
        except Exception, ex:
            syslog.syslog(syslog.LOG_INFO,
                          'collector thread failed to connect to database, stopping')
            return

        if not db_engine or not db:
            syslog.syslog(syslog.LOG_INFO,
                          'collector thread failed to connect to database, stopping')
            return

        db_queue = Queue(self.config["general"]["database_queue_size"])

        dbt = dt.DatabaseThread(self.root, self.config, db_queue)
        dbt.start()

        while self.running:
            engines = db.query(Engine).filter(Engine.active == 1)
            for engine in engines:
                if self.has_thread(engine):
                    continue

                syslog.syslog(syslog.LOG_INFO, "starting thread for engine: " + str(engine.name))
                e_thread = et.EngineThread(self.thread_queue, 
                                           self.root,
                                           self.config,
                                           db_queue,
                                           engine)
                self.thread_queue.append({
                    "engine": engine,
                    "instance": e_thread
                })
                e_thread.start()
            time.sleep(self.config["general"]["engine_check_interval"])

            self.handle_deleted_engines(engines)

        syslog.syslog(syslog.LOG_INFO, 'shutting down database thread')

        dbt.stop()

        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector has stopped')

