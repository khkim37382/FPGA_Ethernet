#ifndef FPGA_UDP_BRIDGE_H
#define FPGA_UDP_BRIDGE_H

/* Portable reference for an HPS, soft CPU, or embedded Linux bridge.
 * It is deliberately independent of any FPGA vendor SDK. */
#include <stddef.h>
#include <stdint.h>

#define FPGA_UDP_MAGIC 0x46504741u /* ASCII FPGA */
#define FPGA_UDP_VERSION 1u
#define FPGA_UDP_PACKET_TYPE_SAMPLES_U16 1u
#define FPGA_UDP_HEADER_SIZE 26u
#define FPGA_UDP_SAFE_PAYLOAD_MAX 1400u /* avoids MTU-1500 IP fragmentation */

struct fpga_udp_identity {
    uint8_t fpga_id;          /* fixed hardware identity: 1..12 */
    uint8_t packet_type;      /* 1 = network-order uint16 samples */
    uint32_t next_sequence;   /* persist for the duration of an acquisition */
};

/* Builds one complete UDP payload (custom header + application payload).
 * timestamp is a FPGA clock count, not a host wall-clock timestamp.
 * The caller owns output and must provide HEADER_SIZE + payload_length bytes.
 * Returns complete datagram size, or 0 on invalid input. */
size_t fpga_udp_build_packet(struct fpga_udp_identity *identity,
                             uint64_t timestamp,
                             const uint8_t *payload, uint16_t payload_length,
                             uint8_t *output, size_t output_capacity);

/* IEEE 802.3 CRC-32, initial/final XOR handled internally. */
uint32_t fpga_udp_crc32(const uint8_t *data, size_t length);

#endif
