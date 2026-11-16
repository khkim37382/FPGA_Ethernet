#define _POSIX_C_SOURCE 200809L
#include "fpga_udp_bridge.h"
#include "n3_record.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define N3_RECORD_BYTES 28u
#define N3_PACKET_TYPE 2u
#define N3_BRIDGE_ID 0x4e334531u
static volatile sig_atomic_t stop;
static void on_signal(int sig) { (void)sig; stop = 1; }
static unsigned long number(const char *s) {
    char *end;
    errno = 0;
    unsigned long v = strtoul(s, &end, 0);
    if (errno || !*s || *end || *s == '-') { fprintf(stderr, "Invalid number: %s\n", s); exit(2); }
    return v;
}
static uint32_t read_reg(volatile uint32_t *regs, unsigned offset) {
    uint32_t value = regs[offset / 4];
    __sync_synchronize();
    return value;
}
static void write_reg(volatile uint32_t *regs, unsigned offset, uint32_t value) {
    __sync_synchronize();
    regs[offset / 4] = value;
    __sync_synchronize();
}
static uint64_t read_counter(volatile uint32_t *regs, unsigned offset) {
    uint32_t hi, lo, again;
    do {
        hi = read_reg(regs, offset + 4);
        lo = read_reg(regs, offset);
        again = read_reg(regs, offset + 4);
    } while (hi != again);
    return ((uint64_t)hi << 32) | lo;
}
static uint64_t timestamp(const uint8_t *record) {
    uint64_t t = 0;
    for (unsigned i = 0; i < 8; ++i) t = (t << 8) | record[i];
    return t;
}
static void usage(const char *name) {
    fprintf(stderr, "Usage: %s --id 1..12 --dest IPv4 [--port 5000] "
            "[--batch 1..50] [--sequence 0] (--uio /dev/uioN | --input records.bin)\n", name);
}

int main(int argc, char **argv) {
    const char *dest = NULL, *uio = NULL, *input = NULL;
    unsigned long id = 0, port = 5000, batch = 50, sequence = 0;
    for (int i = 1; i < argc; ++i) {
        const char *option = argv[i];
        if (i + 1 == argc) { usage(argv[0]); return 2; }
        const char *value = argv[++i];
        if (!strcmp(option, "--id")) id = number(value);
        else if (!strcmp(option, "--dest")) dest = value;
        else if (!strcmp(option, "--port")) port = number(value);
        else if (!strcmp(option, "--batch")) batch = number(value);
        else if (!strcmp(option, "--sequence")) sequence = number(value);
        else if (!strcmp(option, "--uio")) uio = value;
        else if (!strcmp(option, "--input")) input = value;
        else { usage(argv[0]); return 2; }
    }
    if (!dest || id < 1 || id > 12 || port < 1 || port > 65535 || batch < 1 || batch > 50
        || sequence > UINT32_MAX || (!uio == !input)) { usage(argv[0]); return 2; }
    int result = 1, sock = -1, fd = -1;
    FILE *file = NULL;
    void *mapping = MAP_FAILED;
    volatile uint32_t *regs = NULL;
    size_t map_length = 0;
    struct sockaddr_in address = { .sin_family = AF_INET, .sin_port = htons((uint16_t)port) };
    if (inet_pton(AF_INET, dest, &address.sin_addr) != 1) { fprintf(stderr, "Invalid destination IPv4\n"); goto cleanup; }
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) { perror("socket"); goto cleanup; }
    if (input) {
        file = fopen(input, "rb");
        if (!file) { perror(input); goto cleanup; }
    } else {
        // UIO map0 must describe this component, not the whole HPS bridge.
        if (strncmp(uio, "/dev/uio", 8) || !uio[8] || strspn(uio + 8, "0123456789") != strlen(uio + 8)) {
            fprintf(stderr, "Expected /dev/uioN\n"); goto cleanup;
        }
        char path[256];
        snprintf(path, sizeof path, "/sys/class/uio/%s/maps/map0/size", uio + 5);
        FILE *size_file = fopen(path, "r");
        unsigned long long span = 0;
        if (!size_file) { perror(path); goto cleanup; }
        int parsed = fscanf(size_file, "%llx", &span);
        fclose(size_file);
        if (parsed != 1 || span < 0x80) { fprintf(stderr, "UIO map0 span must be >= 0x80\n"); goto cleanup; }
        snprintf(path, sizeof path, "/sys/class/uio/%s/maps/map0/offset", uio + 5);
        FILE *offset_file = fopen(path, "r");
        unsigned long long offset = 0;
        if (!offset_file) { perror(path); goto cleanup; }
        parsed = fscanf(offset_file, "%llx", &offset);
        fclose(offset_file);
        if (parsed != 1 || offset != 0) { fprintf(stderr, "N3 UIO map0 must have zero map offset\n"); goto cleanup; }
        long page_size = sysconf(_SC_PAGESIZE);
        if (page_size <= 0) { perror("page size"); goto cleanup; }
        map_length = (size_t)page_size;
        fd = open(uio, O_RDWR | O_SYNC);
        if (fd < 0) { perror(uio); goto cleanup; }
        struct flock owner = { .l_type = F_WRLCK, .l_whence = SEEK_SET, .l_start = 0, .l_len = 0 };
        if (fcntl(fd, F_SETLK, &owner) < 0) { perror("lock UIO: another sender may own this bridge"); goto cleanup; }
        mapping = mmap(NULL, map_length, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (mapping == MAP_FAILED) { perror("mmap"); goto cleanup; }
        regs = mapping;
        if (read_reg(regs, 0) != N3_BRIDGE_ID || read_reg(regs, 4) != 0x00010000u || read_reg(regs, 0x58) != 50000000u) {
            fprintf(stderr, "Wrong N3 bridge ID/version/timestamp frequency\n"); regs = NULL; goto cleanup;
        }
        if (read_reg(regs, 8) & 1u) {
            fprintf(stderr, "Bridge already enabled; stop its owner before starting another sender\n");
            regs = NULL; goto cleanup;
        }
        write_reg(regs, 8, 1);
    }
    signal(SIGINT, on_signal); signal(SIGTERM, on_signal);
    struct fpga_udp_identity identity = { (uint8_t)id, N3_PACKET_TYPE, (uint32_t)sequence };
    uint8_t payload[1400], packet[FPGA_UDP_HEADER_SIZE + 1400];
    uint64_t packets = 0, records = 0;
    int eof = 0;
    while (!stop && !eof) {
        unsigned count = 0;
        while (!stop && count < batch) {
            uint8_t *out = payload + count * N3_RECORD_BYTES;
            if (file) {
                size_t n = fread(out, 1, N3_RECORD_BYTES, file);
                if (n != N3_RECORD_BYTES) {
                    if (n || ferror(file)) { fprintf(stderr, "Truncated or unreadable 28-byte record\n"); goto cleanup; }
                    eof = 1; break;
                }
            } else {
                uint32_t status = read_reg(regs, 0x0c);
                if (!(status & 4u)) {
                    if (status & 1u) break;
                    write_reg(regs, 0x10, 1); // latch/pop one whole record
                    if (!(read_reg(regs, 0x0c) & 4u)) {
                        fprintf(stderr, "Record capture failed\n"); goto cleanup;
                    }
                }
                // DATA0 is the low word of {timestamp[63:0], raw_n3[159:0]}.
                uint32_t words[7];
                for (unsigned word = 0; word < 7; ++word) words[word] = read_reg(regs, 0x20 + 4 * word);
                n3_record_serialize(words, out);
                write_reg(regs, 0x10, 2); // release stable latch
            }
            ++count;
        }
        if (!count) {
            if (!file) { struct timespec delay = {0, 100000}; nanosleep(&delay, NULL); }
            continue;
        }
        size_t length = fpga_udp_build_packet(&identity, timestamp(payload), payload,
                              (uint16_t)(count * N3_RECORD_BYTES), packet, sizeof packet);
        if (!length) { fprintf(stderr, "Packet build failed\n"); goto cleanup; }
        if (sendto(sock, packet, length, 0, (struct sockaddr *)&address, sizeof address) != (ssize_t)length) {
            perror("sendto"); goto cleanup;
        }
        ++packets; records += count;
    }
    fprintf(stdout, "fpga=%lu packets=%" PRIu64 " records=%" PRIu64 " next_sequence=%" PRIu32 "\n",
            id, packets, records, identity.next_sequence);
    result = 0;
cleanup:
    if (regs) {
        write_reg(regs, 8, 0);
        fprintf(stderr, "accepted=%" PRIu64 " consumed=%" PRIu64 " stalled_cycles=%" PRIu64 " queued=%" PRIu32 "\n",
                read_counter(regs, 0x40), read_counter(regs, 0x48), read_counter(regs, 0x50), read_reg(regs, 0x14));
    }
    if (mapping != MAP_FAILED) munmap(mapping, map_length);
    if (fd >= 0) close(fd);
    if (file) fclose(file);
    if (sock >= 0) close(sock);
    return result;
}
