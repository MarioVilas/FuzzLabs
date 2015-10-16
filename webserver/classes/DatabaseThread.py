import json
import syslog
import threading
import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from classes.database.Base import Base
from classes.database.Engine import Engine
from classes.database.Job import Job
from classes.database.Issue import Issue

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class DatabaseThread(threading.Thread):

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, root, config, data_queue):
        threading.Thread.__init__(self)
        self.root = root
        self.config = config
        self.dqueue = data_queue
        self.running = True
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def disable_engine(self, db, engine):
        engines = db.query(Engine).filter(Engine.id == engine.id).update({Engine.active: 0})
        db.commit()

        db.query(Job).filter(Job.engine_id == engine.id).delete()
        db.commit()

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def handle_job(self, db, engine, active, data):
        if not engine or not data: return

        for job in data:
            c = 0
            try:
                c = db.query(Job).filter(
                            (Job.engine_id == engine.id) &\
                            (Job.job_id == job["job_id"])
                            ).count()
            except Exception, ex:
                syslog.syslog(syslog.LOG_ERR,
                              'failed to get number of jobs: %s' %\
                              str(ex))
                return
            if c == 0:
                try:
                    # TODO: UPDATE TO NEW STRUCTURE
                    n_job = Job(job_id      = job["job_id"],
                                name        = job["name"],
                                engine_id   = engine.id,
                                status      = job["status"],
                                c_m_index   = job["c_m_index"],
                                t_m_index   = job["t_m_index"],
                                crashes     = job["crashes"],
                                warnings    = job["warnings"],
                                job_loaded  = job["job_loaded"],
                                job_started = job["job_started"],
                                job_stopped = job["job_stopped"],
                                session     = json.dumps(job["session"]),
                                target      = json.dumps(job["target"]),
                                conditions  = json.dumps(job["conditions"]),
                                requests    = json.dumps(job["request"]),
                                agent       = json.dumps(job.get("agent")))
                    db.add(n_job)
                    db.commit()
                except Exception, ex: 
                    syslog.syslog(syslog.LOG_ERR,
                                  'failed to add job to the database: %s' %\
                                  str(ex))
                    continue
            else:
                try:
                    n_job = db.query(Job).filter(
                                    (Job.engine_id == engine.id) &\
                                    (Job.job_id == job["job_id"])).one()

                    n_job.name        = job["name"]
                    n_job.status      = job["status"]
                    n_job.c_m_index   = job["c_m_index"]
                    n_job.t_m_index   = job["t_m_index"]
                    n_job.crashes     = job["crashes"]
                    n_job.warnings    = job["warnings"]
                    n_job.job_loaded  = job["job_loaded"]
                    n_job.job_started = job["job_started"]
                    n_job.job_stopped = job["job_stopped"]
                    n_job.session     = json.dumps(job["session"])
                    n_job.target      = json.dumps(job["target"])
                    n_job.conditions  = json.dumps(job["conditions"])
                    n_job.requests    = json.dumps(job["request"])
                    n_job.agent       = json.dumps(job.get("agent"))

                    db.add(n_job)
                    db.commit()
                except Exception, ex: 
                    syslog.syslog(syslog.LOG_ERR,
                                  'failed to update job in database: %s' %\
                                  str(ex))
                    continue

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def handle_issue(self, db, engine, data):
        if not engine or not data: return
        data["engine"] = engine.id

        """
        id        = Column(Integer, primary_key=True)
        job_id    = Column(String(32))
        time      = Column(Integer)
        info      = Column(Text)
        payload   = Column(Text)
        """

        try:
            n_issue = Issue(job_id  = data.get('job_id'),
                            time    = data.get('time'),
                            info    = json.dumps(data.get('info')),
                            payload = data.get('payload'))
        except Exception, ex: 
            syslog.syslog(syslog.LOG_ERR,
                          "failed to process new issue (%s)" % str(ex))
            return

        try:
            db.add(n_issue)
            db.commit()
        except Exception, ex: 
            syslog.syslog(syslog.LOG_ERR,
                          "failed to store new issue (%s)" % str(ex))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def stop(self):
        self.running = False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector DB thread is running')

        try:
            engine = create_engine('sqlite:///' + self.root +\
                                   '/etc/webserver.db', echo=False)
            Session = sessionmaker(bind = engine)
            db = Session()
            Base.metadata.create_all(engine)
            db.commit()
        except Exception, ex:
            syslog.syslog(syslog.LOG_INFO,
                          'collector DB thread failed to connect to database, stopping')
            return

        while self.running:
            task = None
            try:
                task = self.dqueue.get(True, 1)
                if task:
                    if task.get('item') == "engine" and task.get('action') == "disable":
                        self.disable_engine(db, task.get('data'))
                    if task.get('item') == "job" and task.get('action') == "handle":
                        self.handle_job(db, task.get('engine'),
                                        task.get('active'), task.get('data'))
                    if task.get('item') == "issue" and task.get('action') == "handle":
                        self.handle_issue(db, task.get('engine'),
                                          task.get('data'))
            except Queue.Empty:
                pass

        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector DB thread has stopped')

