#include "Common.h"

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

bool Common::isNumber(char *value) {
    long int ret = strtol(value, NULL, 10);
    if (errno == EINVAL || errno == ERANGE) return false;
    return true;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

unsigned int Common::readUntilEOF(char *file, char *buffer) {
    if (file == NULL) return 0;
    unsigned int bytes = 0;
    int fd;

    fd = open(file, O_RDONLY);
    if (fd == -1) return 0;

    buffer = (char *)realloc(buffer, 1);
    if (buffer == NULL) return 0;
    while (read(fd, buffer, 1) != 0) {
        buffer = (char *)realloc(buffer, bytes + 1);
        if (buffer == NULL) break;
        bytes++;
    }
    
    if (bytes == 0 && buffer != NULL) {
        free(buffer);
        buffer = NULL;
    }
    close(fd);
    return bytes;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

char *Common::getCmdLineString(char *buffer, unsigned int size) {
    unsigned int counter = 0;
    char *str = (char *)malloc(size);
    if (str == NULL) return NULL;
    memset(str, 0x00, size);
    for (counter = 0; counter < size; counter++) {
        if (buffer[counter] == 0x00 && buffer[counter + 1] != 0x00) {
            str[counter] = 0x20;
        } else {
            str[counter] = buffer[counter];
        }
    }
    str[counter] = 0x00;
    return str;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

unsigned int Common::readProcCmdLine(unsigned int pid, char *buffer) {
    char sPid[8];
    unsigned int dLength = 0;
    unsigned int bytes = snprintf(sPid, 8, "%d", pid);
    if (strlen(sPid) < bytes) return 0;
    
    char *fullPath = (char *)malloc(24);
    memset(fullPath, 0x00, 24);
    strncat(fullPath, "/proc/", 6);
    strncat(fullPath, sPid, 8);
    strncat(fullPath, "/cmdline", 8);

    dLength = readUntilEOF(fullPath, buffer);
    
    free(fullPath);
    return dLength;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

char *Common::prepProcCmdLine(char *value) {
    if (value == NULL) return NULL;
    unsigned int i = 0;
    for (i = 0; value[i] != 0x00; i++) {
        if (value[i] == 0x20) value[i] = 0x00;
    }
    return(value);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

unsigned int Common::getPidByCmdLine(char *value, unsigned int length) {
    unsigned int child = 0;

    DIR *proc = opendir("/proc");
    if (proc == NULL) {
        syslog(LOG_ERR, "failed to open /proc");
        return(0);
    }
    
    while (1) {
        dirent *entry = readdir(proc);
        if (entry == NULL) break;
        pid_t cur_pid = atoi(entry->d_name);
        if (cur_pid == 0) continue;
        int i_tmp = strlen(entry->d_name) + 16;
        
        char *p_tmp = (char *)malloc(i_tmp);
        if (p_tmp == NULL) {
            syslog(LOG_ERR, "failed to allocate memory: %d", errno);
            return(0);
        }
        memset(p_tmp, 0, i_tmp);
        
        snprintf(p_tmp, i_tmp - 1, "/proc/%s/cmdline", entry->d_name);
        FILE *file = fopen(p_tmp, "r");
        
        if (file == NULL) {
            syslog(LOG_ERR, "failed to open file: %s (%d)", p_tmp, errno);
            free(p_tmp);
            continue;
        }
        
        char tmpbuf[length];
        memset(tmpbuf, 0, length);
        fread(tmpbuf, 1, length, file);
        fclose(file);
        if (strncmp(tmpbuf, value, length) == 0) {
            child = cur_pid;
            free(p_tmp);
            break;
        }
        free(p_tmp);
    }
    closedir(proc);
    return child;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

bool Common::killProcess(unsigned int pid) {
    int error;
    
    syslog(LOG_INFO, "killing process: %d", pid);
    if (kill(pid, SIGKILL) == -1) {
        error = errno;
        if (error == EINVAL || error == EPERM) return false;
        // Even if it is considered as an error that the process
        // does not exist, this is how we report that we got rid
        // of it anyway. So, this is good for us.
        if (error == ESRCH) return true;
    } else {
        return true;
    }
    return false;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

// IMPORTANT TODO: have to send SIGSTOP. Once stopped do the detach.

bool Common::detachProcess(unsigned int pid) {
    syslog(LOG_INFO, "detaching from process: %d", pid);
    if (ptrace(PTRACE_DETACH, pid, NULL, SIGSTOP) == -1) {
        syslog(LOG_ERR, "failed to detach from process: %d", pid);
        return false;
    }
    return true;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

char *Common::getSignalStr(int sign) {
    char *buf = (char *)malloc(256);
    memset(buf, 0x00, 256);
    char *t_s_signal = strsignal(sign);
    if (t_s_signal == NULL) return NULL;
    strncpy(buf, t_s_signal, 255);
    return buf;
}

// ----------------------------------------------------------------------------
// Parse a command line where arguments are separated by space. After parsing
// an array of string pointers is returned where each item in the array points
// to an argument string. The last item in the array is always NULL.
//
// Returns:
//
//  - NULL if the original string is NULL or the length of the string is less
//    than 1.
//
//  Otherwise, it returns an array of string pointers.
//
// ----------------------------------------------------------------------------

char **Common::parseArgs(char *str) {
    if (str == NULL || strlen(str) < 1) return(NULL);

    char **res = NULL;
    int n_spaces = 0;
    int i = 0;

    char *p = strtok(str, " ");

    while(p) {
        res = (char **)realloc(res, sizeof(char*) * ++n_spaces);
        if (res == NULL) exit(-1);
        res[n_spaces-1] = p;
        p = strtok(NULL, " ");
    }

    res = (char **)realloc(res, sizeof(char*) * (n_spaces+1));
    res[n_spaces] = 0;

    return(res);
}

// ----------------------------------------------------------------------------
// Get the command name from the first argument. The result will be used as
// the second argument for exec...()
//
// Returns:
//   - Pointer to the original string if no "/" character found in string
//   - NULL if the original string was NULL or was shorter than 1 byte
//
//   Otherwise, returns the command name extracted from the original string.
//
// ----------------------------------------------------------------------------

char *Common::getCommandName(char *str) {
    if (str == NULL || strlen(str) < 1) return(NULL);
    if (strchr(str, 0x2F) == NULL) return(str);

    char *temp = NULL;

    char *t = strtok(str, "/");
    if (t != NULL) temp = t;
    while(t) {
        t = strtok(NULL, "/");
        if (t != NULL) temp = t;
    }
    return(temp);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

pid_t Common::doStartProcess(target *n_target) {
    char **p_args = NULL;
    pid_t child = fork();

    if (child < 0) return -1;
    if (child == 0) {
        p_args = parseArgs(n_target->t_target_cmdline);
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        execv(p_args[0], p_args);
        exit(1);
    }
    return child;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

bool Common::doAttachProcess(target *n_target) {
    if (ptrace(PTRACE_ATTACH, n_target->pid, NULL, NULL) == -1) return false;
    return true;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

target *Common::getTargetByPid(targets all_targets, pid_t pid) {
    unsigned int counter = 0;
    for (counter = 0; counter < all_targets.n_targets; counter++) {
        if (all_targets.target[counter]->pid == pid) 
            return(all_targets.target[counter]);
    }
    return NULL;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

bool Common::removeTargetFromList(targets all_targets, pid_t pid) {
    unsigned int counter = 0;
    for (counter = 0; counter < all_targets.n_targets; counter++) {
        if (all_targets.target[counter]->pid == pid) {
            free(all_targets.target[counter]);
            all_targets.target[counter] = NULL;
            all_targets.n_targets--;
            return true;
            break;
        }
    }
    return false;
}
