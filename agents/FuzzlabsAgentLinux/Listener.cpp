#include "Listener.h"
#include "Connection.h"

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

static void *start_monitor(void *m) {
    Monitor *monitor = (Monitor *)m;
    monitor->start();
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int handle_command_kill(Connection *conn, Monitor *monitor) {
    if (monitor != NULL) {
        if (monitor->terminate()) {
            conn->transmit("{\"command\": \"kill\", \"data\": \"success\"}", 38);
        } else {
            conn->transmit("{\"command\": \"kill\", \"data\": \"failed\"}", 37);
        }
    } else {
        conn->transmit("{\"command\": \"kill\", \"data\": \"failed\"}", 37);
    }
    return(0);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int handle_command_ping(Connection *conn) {
    conn->transmit("{\"command\": \"ping\", \"data\": \"pong\"}", 35);
    return(0);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

void handle_command_stop(Connection *conn, Monitor *monitor) {
    handle_command_kill(conn, monitor);
    monitor->stop();
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int handle_command_status(Connection *conn, Monitor *monitor) {
    if (monitor == NULL || monitor->isRunning() == 0) {
        conn->transmit("{\"command\": \"status\", \"data\": \"OK\"}", 35);
        return(0);
    }
    
    targets tl = monitor->getTargets();
    if (tl.n_targets == 0) {
        conn->transmit("{\"command\": \"status\", \"data\": \"OK\"}", 35);
        return(0);        
    }

    unsigned int counter = 0;
    
    cJSON *data = cJSON_CreateObject();
    cJSON_AddStringToObject(data, "command", "status");
    for (counter = 0; counter < tl.n_targets; counter++) {
        target *t = tl.target[counter];
        cJSON *j_data = cJSON_CreateObject();
        cJSON_AddNumberToObject(j_data, "running", t->is_running);
        cJSON_AddNumberToObject(j_data, "state", t->state);
        cJSON_AddNumberToObject(j_data, "target_type", t->t_type);
        cJSON_AddNumberToObject(j_data, "process_id", t->pid);
        cJSON_AddStringToObject(j_data, "command_line", t->t_target_cmdline);
        cJSON_AddNumberToObject(j_data, "exit_code", t->exitcode);
        cJSON_AddNumberToObject(j_data, "signal_number", t->signal);
        if (t->sigstr != NULL) {
            cJSON_AddStringToObject(j_data, "signal_string", t->sigstr);
        }
        cJSON_AddItemToObject(data, "data", j_data);
    }
    char *t_json = cJSON_Print(data);
    if (t_json != NULL) conn->transmit(t_json, strlen(t_json));
    cJSON_Delete(data);   
    return(1);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int handle_command_start(Connection *conn, Monitor *monitor, cJSON *data) {
    unsigned int i = 0;
    unsigned int type = 0;
    char *t_data = NULL;
    pthread_t tid;
    cJSON *object;
    
    const char *str_failed = "{\"command\": \"start\", \"data\": \"failed\"}";
    
    if (data == NULL) {
        syslog(LOG_ERR, "[%s]: target not specified in data", 
                conn->address());
        conn->transmit(str_failed, 38);
        return(0);
    }
    
    for (i = 0 ; i < cJSON_GetArraySize(data) ; i++) {
        cJSON *item = cJSON_GetArrayItem(data, i);
        
        object = cJSON_GetObjectItem(item, "command");
        if (object != NULL) {
            type = TYPE_COMMAND;
            t_data = object->valuestring;    
        }
        object = cJSON_GetObjectItem(item, "process");
        if (t_data != NULL && object != NULL) {
            type = TYPE_PROCESS;
            t_data = object->valuestring;
        }
        
        if (monitor->addTarget(type, t_data)) {
            syslog(LOG_ERR, "[%s]: monitor failed to process command line", 
                    conn->address());
            conn->transmit(str_failed, 38);
            return(0);
        }
    }

    targets t = monitor->getTargets();
    for (i = 0 ; i < t.n_targets; i++) {
        syslog(LOG_INFO, "registered target #%d: %s", i, 
                t.target[i]->t_target_cmdline);
    }
    
    if (pthread_create(&tid, NULL, &start_monitor, monitor) != 0) {
        syslog(LOG_ERR, "[%s]: monitor failed to start process", 
                conn->address());
        conn->transmit("{\"command\": \"start\", \"data\": \"failed\"}", 38);
        return(0);
    }
    conn->transmit("{\"command\": \"start\", \"data\": \"success\"}", 39);
    return(1);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

void process_command(Connection *conn, Monitor *monitor, char *data) {
    syslog(LOG_INFO, "[d] received: %s", data);
    cJSON *json = cJSON_Parse(data);
    if (json == NULL) return;
    cJSON *object = cJSON_GetObjectItem(json, "command");
    if (object == NULL) return;
    char *cmd = object->valuestring;
    if (cmd == NULL) return;

    syslog(LOG_INFO, "command received from %s: %s", conn->address(), cmd);

    if (!strcmp(cmd, "ping")) {
        handle_command_ping(conn);
    } else if (!strcmp(cmd, "kill")) {
        handle_command_kill(conn, monitor);
    } else if (!strcmp(cmd, "stop")) {
        handle_command_stop(conn, monitor);
    } else if (!strcmp(cmd, "start")) {
        handle_command_start(conn, monitor, 
                cJSON_GetObjectItem(json, "data"));
    } else if (!strcmp(cmd, "status")) {
        handle_command_status(conn, monitor);
    }
    
    if (json != NULL) cJSON_Delete(json);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

static void *handle_connection(void *c) {
    size_t r_len = 1;
    Monitor *monitor = new Monitor();
    Connection *conn = (Connection *)c;
    char *data = NULL;
    
    syslog(LOG_INFO, "accepted connection from engine: %s", conn->address());

    while(r_len != 0) {
        try {
            data = conn->receive(data);
            if (r_len < 1 || data == NULL) continue;
            process_command(conn, monitor, data);
            free(data);
            data = NULL;
        } catch(char const* ex) {
            syslog(LOG_ERR, "%s", ex);
            continue;
        }
    }

    syslog(LOG_INFO, "disconnected from engine: %s", conn->address());

    if (monitor != NULL) {
        monitor->terminate();
        monitor->stop();
        delete monitor;
    }
    conn->terminate();
    delete conn;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

void listener(unsigned int port, unsigned int max_conn) {
    int sd, n_sd;
    socklen_t c_len;
    struct sockaddr_in s_addr, c_addr;
    unsigned int running = 1;
    pthread_t tid[max_conn];

    sd = socket(AF_INET, SOCK_STREAM, 0);
    if (sd < 0) throw "failed to create socket for listener";

    bzero((char *) &s_addr, sizeof(s_addr));
    s_addr.sin_family = AF_INET;
    s_addr.sin_addr.s_addr = INADDR_ANY;
    s_addr.sin_port = htons(port);
    if (bind(sd, (struct sockaddr *) &s_addr, sizeof(s_addr)) < 0) 
        throw "failed to bind listener to address";

    if (listen(sd, max_conn) != 0) throw "failed to set up listener";
    c_len = sizeof(c_addr);

    while (running) {
        n_sd = accept(sd, (struct sockaddr *) &c_addr, &c_len);
        if (n_sd < 0) continue;
        Connection *conn = new Connection(n_sd, &c_addr);
        if (pthread_create(&(tid[0]), NULL, &handle_connection, conn) != 0)
            throw "failed to accept connection";
    }
}
