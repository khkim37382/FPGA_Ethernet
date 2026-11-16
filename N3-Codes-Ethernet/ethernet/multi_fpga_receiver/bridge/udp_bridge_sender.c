/* Example POSIX bridge executable. Replace make_samples() with FIFO/DMA reads. */
#include "fpga_udp_bridge.h"
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 4) { fprintf(stderr, "usage: %s DESTINATION_IP FPGA_ID PACKETS\n", argv[0]); return 2; }
    int fpga_id = atoi(argv[2]), packets = atoi(argv[3]);
    if (fpga_id < 1 || fpga_id > 12 || packets < 1) return 2;
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in destination = { .sin_family = AF_INET, .sin_port = htons(5000) };
    if (sock < 0 || inet_pton(AF_INET, argv[1], &destination.sin_addr) != 1) return 1;
    struct fpga_udp_identity id = { .fpga_id = (uint8_t)fpga_id, .packet_type = FPGA_UDP_PACKET_TYPE_SAMPLES_U16 };
    uint8_t payload[512], datagram[FPGA_UDP_HEADER_SIZE + sizeof payload];
    for (int packet = 0; packet < packets; ++packet) {
        for (unsigned i = 0; i < sizeof payload; i += 2) { payload[i] = (uint8_t)(packet >> 8); payload[i + 1] = (uint8_t)packet; }
        size_t bytes = fpga_udp_build_packet(&id, (uint64_t)packet * 256u, payload, sizeof payload, datagram, sizeof datagram);
        if (!bytes || sendto(sock, datagram, bytes, 0, (struct sockaddr *)&destination, sizeof destination) != (ssize_t)bytes) return 1;
    }
    close(sock); return 0;
}
