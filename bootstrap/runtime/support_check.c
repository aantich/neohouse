/* SPDX-License-Identifier: MIT
 * Exercise the bootstrap support layer in the guest before handing it to RTS.
 */
#include "platform.h"
#include "Rts.h"
#include "sm/OSMem.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
extern double house_pow2(double, double);

static void require(int condition, const char *message)
{ if (!condition) house_panic(message); }
static int compare(const void *a, const void *b)
{ int x = *(const int *)a, y = *(const int *)b; return (x > y) - (x < y); }
static void pattern(const unsigned char *p, size_t n, unsigned char value)
{ for (size_t i = 0; i < n; ++i) require(p[i] == value, "metadata payload corruption"); }

void house_support_check(void)
{
    unsigned char *slots[32] = {0};
    size_t sizes[32] = {0};
    uint32_t random = 0x172951;
    for (unsigned round = 0; round < 2048; ++round) {
        random = random * 1664525u + 1013904223u;
        unsigned i = (random >> 16) % 32;
        size_t size = (random >> 8) % 4096 + 1;
        if (slots[i]) pattern(slots[i], sizes[i], i + 1);
        unsigned char *p = realloc(slots[i], size);
        require(p != NULL && !((uintptr_t)p % 16), "metadata allocation/alignment");
        if (slots[i]) pattern(p, size < sizes[i] ? size : sizes[i], i + 1);
        memset(p, i + 1, size); slots[i] = p; sizes[i] = size;
        if (round % 3 == 0) { free(slots[i]); slots[i] = NULL; sizes[i] = 0; }
    }
    for (unsigned i = 0; i < 32; ++i) { if (slots[i]) pattern(slots[i], sizes[i], i + 1); free(slots[i]); }
    void *large = malloc(7 * 1024 * 1024);
    require(large != NULL, "metadata free chunks failed to coalesce"); free(large);
    volatile size_t oversized_count = SIZE_MAX;
    require(calloc(oversized_count, 2) == NULL, "calloc overflow accepted");

    int values[257], sum = 0, after = 0;
    for (unsigned i = 0; i < 257; ++i) { values[i] = (int)(i * 47 % 101) - 50; sum += values[i]; }
    qsort(values, 257, sizeof values[0], compare);
    for (unsigned i = 0; i < 257; ++i) {
        after += values[i];
        if (i) require(values[i-1] <= values[i], "support sort order");
    }
    require(sum == after, "support sort lost values");

    char text[64];
    require(snprintf(text, sizeof text, "%llu %d %08x", UINT64_C(18446744073709551615), -42, 0x1234) == 33,
            "diagnostic length");
    require(strcmp(text, "18446744073709551615 -42 00001234") == 0, "diagnostic formatting");
    require(snprintf(text, 4, "%s", "abcdef") == 6 && strcmp(text, "abc") == 0, "diagnostic truncation");
    const double cases[][2] = {{0, 1}, {1, 2}, {-3, 0.125}, {0.25, 1.189207115002721}, {3.5, 11.313708498984761}};
    for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        double difference = house_pow2(2, cases[i][0]) - cases[i][1];
        require(difference < 1e-12 && difference > -1e-12, "collector exponentiation");
    }

    unsigned char *first = osGetMBlocks(2), *second = osGetMBlocks(1);
    require(first && second && !((uintptr_t)first % (1024 * 1024)), "megablock allocation/alignment");
    memset(first, 0x5a, 2 * 1024 * 1024); second[0] = 0xc3;
    osFreeMBlocks(first, 2);
    unsigned char *reused = osGetMBlocks(1);
    require(reused == first && reused[0] == 0 && second[0] == 0xc3, "megablock reuse/isolation");
    osFreeMBlocks(reused, 1); osFreeMBlocks(second, 1);
    house_message("Bootstrap allocator, formatter, sort and clock-math checks passed\r\n");
}
