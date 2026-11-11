/* SPDX-License-Identifier: MIT */
#pragma once
#include <stddef.h>
#include <stdint.h>
void house_console_byte(uint8_t byte);
void house_message(const char *text);
__attribute__((noreturn)) void house_panic(const char *text);
__attribute__((noreturn)) void house_test_exit(uint32_t failed);
void house_memory_init(void);
void house_faults_init(void);
void house_support_check(void);
void house_rts_init(void);
