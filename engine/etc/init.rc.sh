#!/bin/sh
# Author: Zsolt Imre <zsolt.imre@dcnws.com>

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="FuzzLabs engine service"
NAME=engine
PYTHON=/usr/bin/python
DAEMON="${PYTHON} {{{ENGINE_HOME}}}/$NAME.py"
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

# Read configuration variable file if it is present
[ -r /etc/default/$NAME ] && . /etc/default/$NAME

# Load the VERBOSE setting and other rcS variables
. /lib/init/vars.sh

# Define LSB log_* functions.
# Depend on lsb-base (>= 3.2-14) to ensure that this file is present
# and status_of_proc is working.
. /lib/lsb/init-functions

case "$1" in
  start)
	[ "$VERBOSE" != no ] && log_daemon_msg "Starting $DESC" "$NAME"
	${DAEMON} start
        exit $?
	;;
  stop)
	[ "$VERBOSE" != no ] && log_daemon_msg "Stopping $DESC" "$NAME"
	${DAEMON} stop
        exit $?
	;;
  restart)
	#
	# If the "reload" option is implemented then remove the
	# 'force-reload' alias
	#
	log_daemon_msg "Restarting $DESC" "$NAME"
	${DAEMON} restart
        exit $?
	;;
  *)
	echo "Usage: $SCRIPTNAME {start|stop|restart}" >&2
	exit 3
	;;
esac

