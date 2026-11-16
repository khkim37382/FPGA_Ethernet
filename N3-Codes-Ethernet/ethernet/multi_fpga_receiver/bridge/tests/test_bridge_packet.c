#include "../fpga_udp_bridge.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    uint8_t payload[] = {0x12, 0x34, 0xab, 0xcd};
    uint8_t packet[30];
    struct fpga_udp_identity id = { .fpga_id = 7, .packet_type = 1, .next_sequence = 42 };
    assert(fpga_udp_build_packet(&id, 99, payload, sizeof payload, packet, sizeof packet) == sizeof packet);
    /* Entire expected wire image generated independently by src/packet.py,
       including big-endian CRC 0xf447e588. */
    const uint8_t expected[] = {
        0x46,0x50,0x47,0x41,1,7,1,0,0,0,0,42,0,0,0,0,0,0,0,99,0,4,
        0xf4,0x47,0xe5,0x88,0x12,0x34,0xab,0xcd
    };
    for (unsigned i = 0; i < sizeof expected; ++i) assert(packet[i] == expected[i]);
    assert(id.next_sequence == 43);
    puts("bridge packet self-test passed");
    return 0;
}
