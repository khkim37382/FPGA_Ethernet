#ifndef N3_RECORD_H
#define N3_RECORD_H
#include <stdint.h>

/* DATA0..DATA6 are the low-to-high words of {ticks[63:0], N3[159:0]}.
 * Serialize the complete 224-bit record most significant byte first. */
static inline void n3_record_serialize(const uint32_t words[7], uint8_t output[28]) {
    for (unsigned word = 0; word < 7; ++word) {
        uint32_t value = words[6 - word];
        for (unsigned byte = 0; byte < 4; ++byte)
            output[4 * word + byte] = (uint8_t)(value >> (24 - 8 * byte));
    }
}
#endif
