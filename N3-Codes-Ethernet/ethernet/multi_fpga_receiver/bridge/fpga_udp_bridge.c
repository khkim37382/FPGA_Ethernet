#include "fpga_udp_bridge.h"

static void put_u16_be(uint8_t *p, uint16_t x) { p[0] = (uint8_t)(x >> 8); p[1] = (uint8_t)x; }
static void put_u32_be(uint8_t *p, uint32_t x) {
    p[0] = (uint8_t)(x >> 24); p[1] = (uint8_t)(x >> 16); p[2] = (uint8_t)(x >> 8); p[3] = (uint8_t)x;
}
static void put_u64_be(uint8_t *p, uint64_t x) {
    for (unsigned i = 0; i < 8; ++i) p[i] = (uint8_t)(x >> (56u - 8u * i));
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? 0xedb88320u : 0u);
    }
    return crc;
}

uint32_t fpga_udp_crc32(const uint8_t *data, size_t length) {
    return crc32_update(0xffffffffu, data, length) ^ 0xffffffffu;
}

size_t fpga_udp_build_packet(struct fpga_udp_identity *identity, uint64_t timestamp,
                             const uint8_t *payload, uint16_t payload_length,
                             uint8_t *output, size_t output_capacity) {
    size_t packet_length = FPGA_UDP_HEADER_SIZE + (size_t)payload_length;
    if (!identity || !output || (!payload && payload_length) || identity->fpga_id < 1 ||
        identity->fpga_id > 12 || packet_length > output_capacity) return 0;
    put_u32_be(output + 0, FPGA_UDP_MAGIC);
    output[4] = FPGA_UDP_VERSION;
    output[5] = identity->fpga_id;
    output[6] = identity->packet_type;
    output[7] = 0; /* reserved flags */
    put_u32_be(output + 8, identity->next_sequence++); /* increments for every packet built */
    put_u64_be(output + 12, timestamp);
    put_u16_be(output + 20, payload_length);
    for (uint16_t i = 0; i < payload_length; ++i) output[26 + i] = payload[i];
    /* CRC covers header 0..21 and payload, excluding its own field at 22..25. */
    uint32_t crc = crc32_update(0xffffffffu, output, 22);
    crc = crc32_update(crc, payload, payload_length) ^ 0xffffffffu;
    put_u32_be(output + 22, crc);
    return packet_length;
}
