/* SPDX-License-Identifier: MIT */
OUTPUT_FORMAT(elf32-i386)
OUTPUT_ARCH(i386)
ENTRY(_start)

PHDRS
{
    code PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
}

SECTIONS
{
    . = 0x00100000;
    .multiboot : { KEEP(*(.multiboot)) } :code
    .text ALIGN(16) : { *(.text .text.*) } :code
    .rodata ALIGN(16) : { *(.rodata .rodata.*) } :code
    .data ALIGN(4096) : { *(.data .data.*) } :data
    .bss ALIGN(16) (NOLOAD) : { *(.bss .bss.*) *(COMMON) } :data
    house_kernel_end = .;
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
