/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include "Rts.h"
#include "rts/Flags.h"
#include "platform.h"
#include <string.h>
#include "sm/OSMem.h"
#include "rts/storage/MBlock.h"

extern StgClosure HouseKernel_entry_closure;
extern void (*__init_array_start[])(void);
extern void (*__init_array_end[])(void);

static inline void out8(uint16_t port, uint8_t value)
{
    __asm__ volatile ("outb %0, %1" : : "a"(value), "d"(port));
}

static inline uint8_t in8(uint16_t port)
{
    uint8_t value;
    __asm__ volatile ("inb %1, %0" : "=a"(value) : "d"(port));
    return value;
}

void house_console_byte(uint8_t byte)
{
    while (!(in8(0x3fd) & 0x20)) {}
    out8(0x3f8, byte);
}

void house_message(const char *text)
{
    while (*text) house_console_byte((uint8_t)*text++);
}

__attribute__((noreturn)) void house_test_exit(uint32_t failed)
{
    uint32_t value = failed ? 0x11 : 0x10;
    __asm__ volatile ("outl %0, %1" : : "a"(value), "d"((uint16_t)0xf4));
    for (;;) __asm__ volatile ("cli; hlt");
}

void house_panic(const char *text)
{
    house_message("PANIC: ");
    house_message(text);
    house_message("\r\n");
    house_test_exit(1);
}

void house_unsupported_callback(void) { house_panic("unsupported Haskell platform callback"); }

uint32_t house_gc_count(void) { RTSStats stats; getRTSStats(&stats); return stats.gcs; }
uint32_t house_allocated_bytes(void) { RTSStats stats; getRTSStats(&stats); return stats.allocated_bytes; }
uint32_t house_heap_capacity_mb(void) { return getPhysicalMemorySize() / (1024 * 1024); }
uint32_t house_mblocks_in_use(void) { return mblocks_allocated; }
uint32_t house_in8(uint32_t port) { return in8(port); }
void house_out8(uint32_t port, uint32_t byte) { out8(port, byte); }

uint32_t house_interactive(void)
{
    extern uint32_t house_boot_info;
    const uint32_t *boot = (const void *)(uintptr_t)house_boot_info;
    if (!(boot[0] & (1u << 2))) return 0;
    const char *command = (const void *)(uintptr_t)boot[4];
    /* QEMU prefixes the kernel filename to its -append string. */
    size_t length = strnlen(command, 4096);
    const char option[] = "house.shell=1";
    for (size_t i = 0; i + sizeof option - 1 <= length; ++i)
        if ((!i || command[i-1] == ' ') && !strncmp(command + i, option, sizeof option - 1) &&
            (i + sizeof option - 1 == length || command[i + sizeof option - 1] == ' ')) return 1;
    return 0;
}

void house_runtime_main(void)
{
    house_faults_init();
    house_memory_init();
    house_support_check();
    house_message("Initializing static constructors\r\n");
    for (void (**f)(void) = __init_array_start; f < __init_array_end; ++f) (*f)();
    house_message("Initializing GHC RTS\r\n");
    house_rts_init();
    house_message("Scheduling Haskell entry\r\n");
    Capability *cap = rts_lock();
    HaskellObj result;
    rts_evalIO(&cap, &HouseKernel_entry_closure, &result);
    SchedulerStatus status = rts_getSchedStatus(cap);
    rts_unlock(cap);
    house_message(status == Success ? "Haskell entry completed\r\n" : "Haskell entry failed\r\n");
    house_test_exit(status != Success);
}
