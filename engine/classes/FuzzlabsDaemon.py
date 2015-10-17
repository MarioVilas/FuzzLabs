""" Implement FuzzLabs daemon """

import os
import sys
import time
import signal

from classes.ModuleHandler import ModuleHandler
from classes.DatabaseHandler import DatabaseHandler

class FuzzlabsDaemon():
    """
    Implement the FuzzLabs daemon which loads up modules and keeps track of
    any changes both to the loaded and new modules. Once the daemon is finished
    running the modules are unloaded.
    """

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, root, config):
        """
        Initialize FuzzLabs daemon.

        @type  root:     String
        @param root:     Full path to the FuzzLabs root directory
        @type  config:   Dictionary
        @param config:   The complete configuration as a dictionary
        """

        self.root            = root
        self.config          = config
        self.modules         = None
        self.stdin_path      = self.config['daemon']['stdin']
        self.stdout_path     = self.config['daemon']['stdout']
        self.stderr_path     = self.config['daemon']['stderr']
        self.pidfile_path    = self.config['daemon']['pidfile']
        self.pidfile_timeout = self.config['daemon']['pidfile_timeout']
        self.running         = True
        self.database        = DatabaseHandler(self.config, self.root)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __sigterm_handler(self, signum, frame):
        """
        Handle SIGTERM signal and abort execution.
        """

        self.database.log("info", "DCNWS FuzzLabs is stopping")
        self.running = False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        """
        Main function of FuzzLabs.
        """

        self.database.log("info", "DCNWS FuzzLabs is initializing")

        try:
            os.setsid()
            os.umask(077)
            signal.signal(signal.SIGTERM, self.__sigterm_handler) 
        except Exception, ex:
            self.database.log("error", "failed to start daemon", str(ex))
            sys.exit(1)

        try:
            self.modules = ModuleHandler(self.root, self.config)
        except Exception, ex:
            self.database.log("error", "failed to load modules", str(ex))
            sys.exit(1)

        while self.running:
            time.sleep(1)

        try:
            self.modules.unload_modules()
        except Exception, ex:
            self.database.log("error", "failed to unload modules", str(ex))
            raise Exception(ex)

