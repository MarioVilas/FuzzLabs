#include "Monitor.h"

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

Monitor::Monitor() {
    unsigned int counter = 0;
    all_targets.n_targets = 0;
    for (counter = 0; counter < MAX_TARGET_PROCESSES; counter++) {
        all_targets.target[counter] = NULL;
    }
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

Monitor::~Monitor() {
    terminate();
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

void Monitor::stop() {
    running = 0;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int Monitor::isRunning() {
    return(running);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

targets Monitor::getTargets() {
    return(all_targets);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

void Monitor::freeTarget(target *n_target) {
    if (n_target->t_target_cmdline != NULL)
        free(n_target->t_target_cmdline);
    if (n_target->t_target_cmdline_proc != NULL)
        free(n_target->t_target_cmdline_proc);
    if (n_target->sigstr != NULL)
        free(n_target->sigstr);
    if (n_target != NULL) free(n_target);
    n_target = NULL;
}

// ----------------------------------------------------------------------------
// 
// ----------------------------------------------------------------------------

int Monitor::addTarget(unsigned int type, char *cmd_line) {
    unsigned int counter = 0;

    if (all_targets.n_targets == MAX_TARGET_PROCESSES) return(-1);    
    if (cmd_line == NULL) return(-1);
    unsigned int pLen = 0;

    // 1. Set up n_target. n_target should contain full details of the target,
    //    including:
    //      - Full command line
    //      - Current process ID (if the process is running at the moment)
    
    struct target *n_target = (target *)malloc(sizeof(target));
    if (n_target == NULL) return(-1);
    
    n_target->t_type = type;
    n_target->is_running = false;
    n_target->state = STATE_NOINIT;
    n_target->signal = 0;
    n_target->exitcode = 0;
    n_target->sigstr = NULL;
    n_target->detach = false;
    
    switch(type) {
        case TYPE_COMMAND: {
            n_target->t_target_cmdline = (char *)malloc(strlen(cmd_line));
            if (n_target->t_target_cmdline == NULL) {
                free(n_target);
                return(-1);
            }
            strcpy(n_target->t_target_cmdline, cmd_line);
            n_target->t_target_cmdline_proc = (char *)malloc(strlen(cmd_line));
            if (n_target->t_target_cmdline_proc == NULL) {
                free(n_target->t_target_cmdline);
                free(n_target);
                return(-1);
            }
            strcpy(n_target->t_target_cmdline_proc, 
                    Common::prepProcCmdLine(cmd_line));
            }
            n_target->pid = Common::getPidByCmdLine(
                    n_target->t_target_cmdline_proc, 
                    strlen(n_target->t_target_cmdline));
            if (n_target->pid == 0) {
                n_target->is_running = false;
            } else {
                n_target->is_running = true;
            }
            break;
        case TYPE_PROCESS: {
            if (Common::isNumber(cmd_line) == false) return(-1);
            n_target->pid = atoi(cmd_line);
            pLen = Common::readProcCmdLine(n_target->pid, 
                    n_target->t_target_cmdline_proc);
            if (n_target->t_target_cmdline_proc == NULL || pLen == 0) {
                free(n_target);
                return(-1);
            }
            n_target->t_target_cmdline = Common::getCmdLineString(
                    n_target->t_target_cmdline_proc,
                    pLen);
            if (n_target->t_target_cmdline == NULL) {
                free(n_target->t_target_cmdline_proc);
                free(n_target);
                return(-1);
            }
            n_target->is_running = true;
            }
            break;
        default:
            return(-1);
    }

    // 2. Check if the target was already added
    //    If the target was already added, free up each n_target members
    //    and n_target itself then return.
    
    if (all_targets.n_targets != 0) {
        for (counter = 0; counter < all_targets.n_targets; counter++) {
            if (strcmp(all_targets.target[counter]->t_target_cmdline, 
                    n_target->t_target_cmdline) == 0) {
                freeTarget(n_target);
                return(-1);
            }
        }
    }

    // 3. Add target to the target list
    
    for (counter = 0; counter < MAX_TARGET_PROCESSES; counter++) {
        if (all_targets.target[counter] == NULL) {
            syslog(LOG_DEBUG, "registering target (%s) to slot #%d", 
                    n_target->t_target_cmdline,
                    counter);
            all_targets.target[counter] = n_target;
            all_targets.n_targets++;
            break;
        }
    }
    
    // TODO: consider adding feedback if there was no free slot.
    
    return(0);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

bool Monitor::terminate() {
    unsigned int counter = 0;
    bool success = true;

    if (all_targets.n_targets == 0) return(0);
    
    for (counter = 0; counter < all_targets.n_targets; counter++) {
        if (all_targets.target[counter]->pid == 0) {
            freeTarget(all_targets.target[counter]);
            continue;
        }
        switch(all_targets.target[counter]->t_type) {
            case TYPE_COMMAND: {
                if (!Common::killProcess(all_targets.target[counter]->pid)) {
                    success = false;
                }
            }
            break;
            case TYPE_PROCESS: {
                all_targets.target[counter]->detach = true;
                kill(all_targets.target[counter]->pid, SIGSTOP);
            }
            break;
        }
    }
    return success;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

bool Monitor::startCommand(target *n_target) {
    int t_pid = 0;
    unsigned int rc = 0;
    struct stat buf;

    char **p_args = Common::parseArgs(n_target->t_target_cmdline);
    if (p_args == NULL) {
        syslog(LOG_ERR, "failed to parse arguments at command start");
        return false;
    }
    if (stat(p_args[0], &buf) == -1) return false;
    free(p_args);
    
    for (rc = 0; rc < RESTART_COUNTER; rc++) {
        t_pid = Common::doStartProcess(n_target);
        if (t_pid > 0) {
            n_target->is_running = true;
            n_target->pid = t_pid;
            n_target->state = STATE_NOINIT;
            syslog(LOG_INFO, "command successfully started: %s",
                    n_target->t_target_cmdline);
            break;
        }
        n_target->state = STATE_ERROR;
        syslog(LOG_ERR, "failed to start command: %s, retrying...",
                n_target->t_target_cmdline);
        sleep(1);
    }
    // Make sure we check here if the target is still running.
    sleep(PROC_ALIVE_TOUT);
    char *temp;
    // readProcCmdLine only returns > 0 if it can read the cmdline
    // from /proc. Obviously if the process is not running, it will
    // not be able to read cmdline therefore will return 0.
    unsigned int tl = Common::readProcCmdLine(n_target->pid, temp);
    if (tl == 0) return false;
    return true;
}

// ----------------------------------------------------------------------------
// TODO: needs refactoring to ensure the target process is really up and
//       running before telling the agent that the target is running.
// ----------------------------------------------------------------------------

int Monitor::start() {
    running = 1;
    siginfo_t s_info;
    unsigned int rc = 0;
    unsigned int counter = 0;

    if (all_targets.n_targets == 0) {
        syslog(LOG_ERR, "no targets to monitor");
        return(-1);
    }
    syslog(LOG_INFO, "starting processes:");
    for (counter = 0; counter < all_targets.n_targets; counter++) {
        syslog(LOG_INFO, "#%d: T%d, P%d, %s", counter,
                all_targets.target[counter]->t_type,
                all_targets.target[counter]->pid,
                all_targets.target[counter]->t_target_cmdline);
        
        switch(all_targets.target[counter]->t_type) {
            case TYPE_COMMAND: {
                for (rc = 0; rc < RESTART_TIMEOUT; rc++) {
                    if (startCommand(all_targets.target[counter])) {
                        rc = 0;
                        break;
                    }
                }
                if (rc != 0) {
                    syslog(LOG_ERR, "failed to start command: %s, giving up.",
                            all_targets.target[counter]->t_target_cmdline);
                    terminate();
                    return(-1);
                }
                syslog(LOG_INFO, "command started: %s",
                        all_targets.target[counter]->t_target_cmdline);
            }
            break;
            case TYPE_PROCESS: {
                if (!Common::doAttachProcess(all_targets.target[counter])) {
                    syslog(LOG_ERR, "failed to attach to process: %d, giving up.",
                            all_targets.target[counter]->pid);
                    terminate();
                    return(-1);                    
                }
                syslog(LOG_INFO, "attached to process with PID: %d",
                        all_targets.target[counter]->pid);
            }
            break;
        }
        all_targets.target[counter]->state = STATE_MONITORING;
    }

    while(running) {
        waitid(P_ALL, -1, &s_info, WEXITED|WSTOPPED);
        target *t = Common::getTargetByPid(all_targets, s_info.si_pid);
        
        switch(s_info.si_code) {
            case CLD_DUMPED:
                syslog(LOG_INFO, "target crashed: %s", t->t_target_cmdline);
                t->signal       = s_info.si_status;
                t->sigstr       = Common::getSignalStr(t->signal);
                t->is_running   = false;
                t->state        = STATE_ISSUE;
                t->exitcode     = 0;
                break;
            case CLD_EXITED:
                syslog(LOG_INFO, "target exited: %s", t->t_target_cmdline);
                t->exitcode     = s_info.si_status;
                t->signal       = 0;
                t->sigstr       = NULL;
                t->is_running   = false;
                t->state        = STATE_EXITED;
                break;
            // TODO: this keeps getting called forever once a process get
            // killed. This causes lots of memory allocation 'cause of 
            // getSignalStr. Have to track down why this is happening.
            case CLD_KILLED:
                syslog(LOG_INFO, "target has been killed: %s", 
                        t->t_target_cmdline);
                t->exitcode     = s_info.si_status;
                t->signal       = 0;
                t->sigstr       = Common::getSignalStr(t->signal);
                t->is_running   = false;
                t->state        = STATE_KILLED;
                break;
            case CLD_STOPPED:
            case CLD_TRAPPED:
                if (t->detach) {
                    Common::detachProcess(t->pid);
                } else {
                    ptrace(PTRACE_CONT, t->pid, NULL, NULL);
                }
                break;
        }
    }
    
    syslog(LOG_INFO, "monitor stopped");
    return(0);
}
