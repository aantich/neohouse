/* SPDX-License-Identifier: MIT */
.code32
.section .text,"ax",@progbits
.macro exception number, has_error=0
.global house_exception_\number
house_exception_\number:
    .if !\has_error
    pushl $0
    .endif
    pushl $\number
    jmp house_exception_common
.endm
.irp vector,0,1,2,3,4,5,6,7,9,15,16,18,19,20,22,23,24,25,26,27,28,31
exception \vector
.endr
.irp vector,8,10,11,12,13,14,17,21,29,30
exception \vector,1
.endr
house_exception_common:
    cli
    cld
    pushal
    leal 32(%esp), %eax
    andl $-16, %esp
    subl $12, %esp
    pushl %eax
    call house_fault
1:  hlt
    jmp 1b
.section .rodata,"a",@progbits
.global house_exception_vectors
house_exception_vectors:
.irp vector,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
.long house_exception_\vector
.endr
.section .note.GNU-stack,"",@progbits
