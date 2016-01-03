#ifndef MONITOR_H
#define	MONITOR_H

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/ptrace.h>
#include <errno.h>
#include <syslog.h>
#include <sys/user.h>
#include "Common.h"

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

#define RESTART_COUNTER 3   // How many times to attempt to start a target.
#define RESTART_TIMEOUT 3   // How long (in seconds) to wait to attempt the
                            // restart of a target.
#define PROC_ALIVE_TOUT 10  // Once the target is started wait PROC_ALIVE_TO
                            // seconds before performing a secondary check to
                            // see if the target is still up and running.

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

class Monitor {  
private:
    int running;
    bool do_attach;
    struct targets all_targets;
    
    char *prepProcCmdLine(char *value);
    void freeTarget(target *n_target);
    bool startCommand(target *n_target);
public:
    Monitor();
    ~Monitor();
    int addTarget(unsigned int type, char *cmd_line);
    int start();
    void stop();
    int isRunning();
    bool terminate();
    targets getTargets();
};

#endif	/* MONITOR_H */
