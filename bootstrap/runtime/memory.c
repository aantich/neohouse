/* SPDX-License-Identifier: MIT */
#include "Rts.h"
#include "sm/OSMem.h"
#include "platform.h"
#include <string.h>

#define MB ((uint32_t)1024 * 1024)
#define BLOCKS 4096
static uint8_t usable[BLOCKS], allocated[BLOCKS];
static uint64_t available_bytes;
extern uint32_t house_boot_info;
extern char house_kernel_end[];

/* Independently declared wire format; no historical multiboot.h is included. */
struct map_entry {
    uint32_t size;
    uint64_t address, length;
    uint32_t type;
} __attribute__((packed));

static uint64_t end_of(uint64_t address, uint64_t length)
{
    if (length > UINT64_MAX - address) house_panic("overflow in boot memory map");
    uint64_t end = address + length;
    return end > UINT64_C(0x100000000) ? UINT64_C(0x100000000) : end;
}

void house_memory_init(void)
{
    uint32_t *boot = (uint32_t *)(uintptr_t)house_boot_info;
    if (!(boot[0] & (1u << 6))) house_panic("Multiboot memory map required");
    uint32_t size = boot[11], address = boot[12];
    if (size > 65536 || address > UINT32_MAX - size)
        house_panic("invalid boot memory map extent");
    uintptr_t reserved_end = (uintptr_t)house_kernel_end;
    if ((uintptr_t)boot > UINT32_MAX - 88) house_panic("invalid boot information");
    if ((uintptr_t)boot + 88 > reserved_end) reserved_end = (uintptr_t)boot + 88;
    if (address + size > reserved_end) reserved_end = address + size;
    if (boot[0] & (1u << 2)) {
        uint32_t command = boot[4];
        if (command > UINT32_MAX - 4096) house_panic("invalid boot command line");
        size_t length = strnlen((const char *)(uintptr_t)command, 4096);
        if (length == 4096) house_panic("unterminated boot command line");
        if (command + length + 1 > reserved_end) reserved_end = command + length + 1;
    }
    if (boot[0] & (1u << 3)) {
        uint32_t count = boot[5], modules = boot[6];
        if (count > 64 || modules > UINT32_MAX - count * 16)
            house_panic("invalid boot modules");
        if (modules + count * 16 > reserved_end) reserved_end = modules + count * 16;
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t *module = (uint32_t *)(uintptr_t)(modules + i * 16);
            if (module[1] < module[0]) house_panic("invalid boot module range");
            if (module[1] > reserved_end) reserved_end = module[1];
        }
    }
    /* First admit whole available megablocks, then exclude any reserved overlap.
     * This handles firmware maps containing overlapping reserved entries. */
    for (unsigned pass = 0; pass != 2; ++pass) {
        for (uint32_t offset = 0; offset < size;) {
            if (size - offset < sizeof(struct map_entry)) house_panic("short memory map entry");
            const struct map_entry *entry = (const void *)(uintptr_t)(address + offset);
            if (entry->size < 20 || entry->size > size - offset - 4)
                house_panic("invalid memory map entry size");
            uint64_t begin = entry->address, end = end_of(begin, entry->length);
            if (begin < UINT64_C(0x100000000) && begin < end) {
                uint32_t first = pass ? begin / MB : (begin + MB - 1) / MB;
                uint32_t last = pass ? (end + MB - 1) / MB : end / MB;
                if ((!pass && entry->type == 1) || (pass && entry->type != 1))
                    for (uint32_t i = first; i < last; ++i) usable[i] = !pass;
            }
            offset += entry->size + 4;
        }
    }
    for (uint32_t i = 0; i < BLOCKS; ++i) {
        if ((uint64_t)i * MB < reserved_end) usable[i] = 0;
        if (usable[i]) available_bytes += MB;
    }
    if (available_bytes < 32 * MB) house_panic("less than 32 MiB usable guest heap");
    house_message("Boot memory map accepted; kernel and boot data excluded\r\n");
}

void osMemInit(void) {}
void *osGetMBlocks(uint32_t count)
{
    if (!count || count > BLOCKS) return NULL;
    uint32_t run = 0;
    for (uint32_t i = 0; i < BLOCKS; ++i) {
        run = usable[i] && !allocated[i] ? run + 1 : 0;
        if (run == count) {
            uint32_t first = i + 1 - count;
            for (uint32_t j = first; j <= i; ++j) allocated[j] = 1;
            void *result = (void *)(uintptr_t)(first * MB);
            memset(result, 0, (size_t)count * MB);
            return result;
        }
    }
    return NULL;
}

void osFreeMBlocks(void *address, uint32_t count)
{
    uint32_t start = (uintptr_t)address / MB;
    if ((uintptr_t)address % MB || !count || count > BLOCKS - start)
        house_panic("invalid megablock free");
    for (uint32_t i = start; i < start + count; ++i)
        if (!allocated[i]) house_panic("megablock double free");
    for (uint32_t i = start; i < start + count; ++i) allocated[i] = 0;
}

/* There is no pageable host mapping to relinquish. Released physical blocks
 * remain in the allocator and are reused by subsequent allocations. */
void osReleaseFreeMemory(void) {}
void osFreeAllMBlocks(void) { memset(allocated, 0, sizeof allocated); }
size_t getPageSize(void) { return 4096; }
StgWord64 getPhysicalMemorySize(void) { return available_bytes; }
bool osBuiltWithNumaSupport(void) { return false; }
bool osNumaAvailable(void) { return false; }
uint32_t osNumaNodes(void) { return 1; }
uint64_t osNumaMask(void) { return 1; }
void osBindMBlocksToNode(void *address STG_UNUSED, StgWord size STG_UNUSED, uint32_t node)
{ if (node) house_panic("invalid NUMA node"); }
