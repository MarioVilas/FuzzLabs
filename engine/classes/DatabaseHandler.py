import json
import time
import hashlib
import inspect
import syslog
from pymongo import MongoClient

class DatabaseHandler:

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, config = None, root = None):

        if config == None or root == None:
            return

        self.config   = config
        self.root     = root
        self.dbclient = MongoClient(self.config['general']['database'])
        self.database = self.dbclient.engine
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def saveSession(self, data = None):
        if not data: return False
        try:
            self.database.sessions.insert(data)
        except Exception, ex:
            self.log("critical",
                     "database saveSession() failed",
                     str(ex))
	    return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def loadSession(self, job_id = None):
        if not job_id: return False
        try:
            r = self.database.sessions.find({"job_id": job_id})
            for session in r:
                return session
            return None
        except Exception, ex:
            self.log("critical",
                     "database loadSession() failed",
                     str(ex))
            return None

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def updateSession(self, job_id, data = None):
        if not data: return False
        try:
            self.database.sessions.update({"job_id": job_id}, data)
        except Exception, ex:
            self.log("critical",
                     "database updateSession() failed",
                     str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def deleteSession(self, job_id = None):
        if not job_id: return False
        try:
            r = self.database.sessions.remove({"job_id": job_id})
        except Exception, ex:
            self.log("critical",
                     "database deleteSession() failed",
                     str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def loadJobs(self):
        """
        Returns a simple list of all jobs in the database.
        """

        jobs_list = []
        try:
            r = self.database.jobs.find()
            for job in r:
                job.pop("_id", None)
                jobs_list.append(job)
            return jobs_list
        except Exception, ex:
            self.log("critical",
                     "database loadJobs() failed",
                     str(ex))
            return None

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def loadJob(self, job_id):
        """
        Returns a job from the database.
        """

        try:
            r = self.database.jobs.find({"job_id": job_id})
            for job in r:
                job.pop("_id", None)
                return job
            return None
        except Exception, ex:
            self.log("critical",
                     "database loadJob() failed",
                     str(ex))
            return None

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def insertJob(self, data = None):
        """
        Insert a new job.
        """

        if not data: return False
        if not data.get('job_id'): return False
        try:
            self.database.jobs.insert(data)
        except Exception, ex:
            self.log("critical",
                     "database insertJob() failed",
                     str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def updateJob(self, job_id, status = None, node = None, crashes = None,
                  warnings = None, c_m_index = None, t_m_index = None):


        try:
            r = self.database.jobs.update({"job_id": job_id}, {
                "$set": {
                    "status":    status,
                    "node":      node,
                    "crashes":   crashes,
                    "warnings":  warnings,
                    "c_m_index": c_m_index,
                    "t_m_index": t_m_index
                }
            })
        except Exception, ex:
            self.log("critical",
                     "database updateJob() failed",
                     str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def deleteJob(self, job_id = None):
        if not job_id: return False
        try:
            r = self.database.jobs.remove({"job_id": job_id})
        except Exception, ex:
            self.log("critical",
                     "database deleteJob() failed",
                     str(ex))
            return False
        return self.deleteSession(job_id)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def saveIssue(self, data):
        if not data: return False

        id = hashlib.sha1(str(time.time()) + ":" +\
                          data.get("job_id") + ":" +\
                          str(data.get("mutant_index"))).hexdigest()
        try:
            r = self.database.issues.insert({
                "id":      id,
                "job_id":  data.get("job_id"),
                "time":    time.time(),
                "info":    {
                    "target":       data.get("target"),
                    "name":         data.get("name"),
                    "mutant_index": data.get("mutant_index"),
                    "process":      data.get("process_status")
                },
                "payload": data.get("request")
            })
        except Exception, ex:
            self.log("critical",
                     "database saveIssue() failed",
                     str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def loadIssues(self):
        """
        Returns a simple list of all issues in the database.
        """

        issue_list = []

        try:
            r = self.database.issues.find()
            for issue in r:
                i_data = {
                     "id":     issue["id"],
                     "job_id": issue["job_id"],
                     "time":   issue["time"]
                }
                issue.pop("_id", None)

                issue_list.append(i_data)
            return issue_list
        except Exception, ex:
            self.log("critical",
                     "database loadIssues() failed",
                     str(ex))
            return issue_list

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def loadIssue(self, id):
        """
        Returns full details of an issues.
        """

        try:
            r = self.database.issues.find({"id": id})
            for issue in r:
                issue.pop("_id", None)
                return issue
            return None
        except Exception, ex:
            self.log("critical",
                     "database loadIssue() failed",
                     str(ex))
            return None

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def deleteIssue(self, id):
        """
        Delete an issue from the database.
        """

        try:
            self.database.issues.remove({"id": id})
        except Exception, ex:
            self.log("critical",
                     "database deleteIssue() failed",
                     str(ex))
            return False
        return True

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def log(self, severity, message = None, errdetail = None):
        if not message:   return False
        if not errdetail: errdetail = ""

        if severity != "debug" and severity != "info" and \
           severity != "warning" and severity != "error" and \
           severity != "critical":
            return False

        caller = inspect.stack()[:2][1]

        try:
            logmsg = {
                "time":      time.time(),
                "severity":  severity,
                "message":   message,
            }

            if severity == "debug" or severity == "error" or\
               severity == "critical":
                logmsg["source"] = {
                    "method": str(caller[3]),
                    "line":   str(caller[2]),
                    "file":   str(caller[1])
                }
                logmsg["exception"] = str(errdetail)

            r = self.database.logs.insert(logmsg)

        except Exception, ex:
            syslog.syslog(syslog.LOG_ERR,
                          "CRITICAL: database log() failed (%s)" %\
                          str(ex))
            return False
        return True

