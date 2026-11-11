/* SPDX-License-Identifier: MIT */
#include "platform.h"
struct gate { uint16_t low, selector; uint8_t zero, flags; uint16_t high; } __attribute__((packed));
static struct gate idt[256];
extern uintptr_t house_exception_vectors[32];

void house_faults_init(void)
{
    for (unsigned i = 0; i < 32; ++i) {
        uintptr_t address = house_exception_vectors[i];
        idt[i] = (struct gate){address & 0xffff, 8, 0, 0x8e, address >> 16};
    }
    const struct { uint16_t limit; uint32_t base; } __attribute__((packed)) pointer = {
        sizeof idt - 1, (uintptr_t)idt
    };
    __asm__ volatile ("lidt %0" : : "m"(pointer));
}

static void hex(uint32_t value)
{
    for (int shift = 28; shift >= 0; shift -= 4)
        house_console_byte("0123456789abcdef"[(value >> shift) & 15]);
}

__attribute__((noreturn)) void house_fault(const uint32_t *frame)
{
    uint32_t cr2;
    __asm__ volatile ("movl %%cr2, %0" : "=r"(cr2));
    house_message("CPU FAULT vector="); hex(frame[0]);
    house_message(" error="); hex(frame[1]);
    house_message(" eip="); hex(frame[2]);
    house_message(" cr2="); hex(cr2);
    house_message("\r\n");
    house_test_exit(1);
}
