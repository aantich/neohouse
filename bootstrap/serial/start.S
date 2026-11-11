/* SPDX-License-Identifier: MIT
 * Original platform-entry checkpoint, written from the Multiboot protocol
 * and UART register interface. No historical House/Gadgets code is used.
 * This checkpoint does not start the Haskell runtime.
 */
.code32
.section .multiboot,"a",@progbits
.balign 4
.long 0x1badb002
.long 0x00000003
.long -(0x1badb002 + 0x00000003)

.section .bss,"aw",@nobits
.balign 16
stack_bottom:
.skip 65536
stack_top:
.global house_boot_magic, house_boot_info
house_boot_magic:
.skip 4
house_boot_info:
.skip 4

.section .rodata,"a",@progbits
success_banner:
.asciz "House platform checkpoint: IA32 entry and COM1 serial OK\r\nHaskell RTS not started.\r\n"
failure_banner:
.asciz "House platform checkpoint: invalid Multiboot entry magic\r\n"

.section .text,"ax",@progbits
.global _start
.type _start,@function
_start:
    cli
    cld
    movl %eax, house_boot_magic
    movl %ebx, house_boot_info
    movl $stack_top, %esp
    andl $-16, %esp
    xorl %ebp, %ebp

    /* COM1: polling, 115200 baud, eight data bits, no parity, one stop bit. */
    movw $0x3f9, %dx
    xorl %eax, %eax
    outb %al, %dx
    movw $0x3fb, %dx
    movb $0x80, %al
    outb %al, %dx
    movw $0x3f8, %dx
    movb $1, %al
    outb %al, %dx
    movw $0x3f9, %dx
    xorb %al, %al
    outb %al, %dx
    movw $0x3fb, %dx
    movb $3, %al
    outb %al, %dx
    movw $0x3fa, %dx
    movb $0xc7, %al
    outb %al, %dx
    movw $0x3fc, %dx
    movb $0x0b, %al
    outb %al, %dx

    movl $success_banner, %esi
    movl $0x10, %edi
    cmpl $0x2badb002, house_boot_magic
    je .Lnext
    movl $failure_banner, %esi
    movl $0x11, %edi
.Lnext:
    lodsb
    testb %al, %al
    jz .Lexit
    movb %al, %bl
.Lready:
    movw $0x3fd, %dx
    inb %dx, %al
    testb $0x20, %al
    jz .Lready
    movb %bl, %al
    movw $0x3f8, %dx
    outb %al, %dx
    jmp .Lnext
.Lexit:
    /* QEMU test device: success value 0x10 produces host exit status 33. */
    movw $0xf4, %dx
    movl %edi, %eax
    outl %eax, %dx
.Lhalt:
    cli
    hlt
    jmp .Lhalt
.size _start, .-_start

.section .note.GNU-stack,"",@progbits
