#!/usr/bin/python

""" Initialize environment for the daemon """

import os
import sys
import inspect
from daemon import runner

from classes.ConfigurationHandler import ConfigurationHandler
from classes.FuzzlabsDaemon import FuzzlabsDaemon

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

CONFIG = None
DAEMON = None

ROOT_DIR = os.path.dirname(
                os.path.abspath(
                    inspect.getfile(inspect.currentframe()
                )))

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    CONFIG = None
    DAEMON = None

    ROOT_DIR = os.path.dirname(
                    os.path.abspath(
                        inspect.getfile(inspect.currentframe()
                    )))
    try:
        CONFIG = ConfigurationHandler(ROOT_DIR + "/etc/engine.config").get()
    except Exception, ex:
        print "[E] failed to load configuration: %s" % str(ex)
        sys.exit(1)

    try:
        DAEMON = FuzzlabsDaemon(ROOT_DIR, CONFIG)
    except Exception, ex:
        print "[E] failed to initialize daemon: %s" % str(ex)
        sys.exit(1)

    try:
        DAEMON_RUNNER = runner.DaemonRunner(DAEMON)
        DAEMON_RUNNER.do_action()
    except Exception, ex:
        print "[E] failed to start/stop daemon: %s" % str(ex)

