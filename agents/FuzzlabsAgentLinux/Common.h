#ifndef COMMON_H
#define	COMMON_H

#include <cstdlib>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <syslog.h>
#include <signal.h>
#include <dirent.h>
#include <string.h>
#include <sys/ptrace.h>

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

#define MAX_TARGET_PROCESSES    32
#define TYPE_COMMAND            0
#define TYPE_PROCESS            1

#define STATE_NOINIT            0
#define STATE_ERROR             1
#define STATE_MONITORING        2
#define STATE_ISSUE             3
#define STATE_EXITED            4

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

struct target {
    // Basic target details
    bool is_running;
    unsigned int t_type;
    unsigned int pid;
    char *t_target_cmdline;
    char *t_target_cmdline_proc;
    // Target status details
    unsigned int state;
    int signal;
    int exitcode;
    char *sigstr;
    // Detach
    bool detach;
};

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

struct targets {
    unsigned int n_targets;
    struct target *target[MAX_TARGET_PROCESSES];
};

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

class Common {
public:
    static bool isNumber(char *value);
    static unsigned int readProcCmdLine(unsigned int pid, char *buffer);
    static char *getCmdLineString(char *buffer, unsigned int size);
    static char *prepProcCmdLine(char *value);
    static unsigned int getPidByCmdLine(char *value, unsigned int length);
    static bool killProcess(unsigned int pid);
    static bool detachProcess(unsigned int pid);
    static char *getSignalStr(int sign);
    static char **parseArgs(char *str);
    static char *getCommandName(char *str);
    static pid_t doStartProcess(target *n_target);
    static bool doAttachProcess(target *n_target);
    static target *getTargetByPid(targets all_targets, pid_t pid);
private:
    static unsigned int readUntilEOF(char *file, char *buffer);
};

#endif	/* COMMON_H */

