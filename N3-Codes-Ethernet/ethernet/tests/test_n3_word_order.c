#include "n3_record.h"
#include <stdio.h>

/* Exercise the UIO sender's serializer with captured Avalon words from RTL. */
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    FILE *input = fopen(argv[1], "rb");
    if (!input) return 1;
    uint8_t source[28], record[28];
    size_t size;
    while ((size = fread(source, 1, sizeof source, input)) != 0) {
        if (size != sizeof source) { fclose(input); return 1; }
        uint32_t words[7];
        for (unsigned i = 0; i < 7; ++i)
            words[i] = (uint32_t)source[4*i] | (uint32_t)source[4*i+1] << 8 |
                       (uint32_t)source[4*i+2] << 16 | (uint32_t)source[4*i+3] << 24;
        n3_record_serialize(words, record);
        if (fwrite(record, 1, sizeof record, stdout) != sizeof record) { fclose(input); return 1; }
    }
    int result = ferror(input) ? 1 : 0;
    fclose(input);
    return result;
}
