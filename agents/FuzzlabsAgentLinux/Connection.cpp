#include "Connection.h"

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

Connection::Connection(int c_fd, struct sockaddr_in *c_sin) {
    sock = c_fd;
    sin = c_sin;
    client_addr = (char *)malloc(256);
    memset(client_addr, 0x00, 256);
    strncpy(client_addr,(char *)inet_ntoa(sin->sin_addr), 255);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

Connection::~Connection() {
    if (client_addr != NULL) free(client_addr);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int Connection::socket() {
    return sock;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

char *Connection::address() {
    return client_addr;
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

int Connection::transmit(const char *data, unsigned int len) {
    return send(sock, data, len, 0);
}

// ----------------------------------------------------------------------------
// Returns:
//     0 - if nothing received
//    -1 - if client closed socket
// ----------------------------------------------------------------------------

unsigned int Connection::receive(char *data) {
    size_t total = 0;
    size_t length = 0;
    char buffer[RECV_BUFFER_SIZE];

    while (true) {
        memset(buffer, 0x00, RECV_BUFFER_SIZE);
        length = recv(sock, buffer, RECV_BUFFER_SIZE - 1, MSG_DONTWAIT);
        
        if (length == -1) break;

        if (total + length > RECV_MAX_MSG_SIZE * 1048576) {
            if (data != NULL) free(data);
            data = NULL;
            throw "Connection::receive(): invalid message size";
        }
        data = (char *)realloc(data, total + length);
        if (data == NULL) {
            throw "Connection::receive(): failed to realloc() data buffer";
        }
        strcpy(data + total, buffer);
        total += length;
    }

    memset(buffer, 0x00, RECV_BUFFER_SIZE);
    return(total);
}

// ----------------------------------------------------------------------------
//
// ----------------------------------------------------------------------------

void Connection::terminate() {
    close(sock);
}
