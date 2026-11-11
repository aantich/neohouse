/* SPDX-License-Identifier: MIT
 * Small single-CPU support layer for the first RTS checkpoint. There are no
 * OS file descriptors here: only explicit serial stdout/stderr streams.
 */
#include "platform.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

void *memcpy(void *to, const void *from, size_t size)
{ unsigned char *d = to; const unsigned char *s = from; while (size--) *d++ = *s++; return to; }
void *memmove(void *to, const void *from, size_t size)
{
    unsigned char *d = to; const unsigned char *s = from;
    if ((uintptr_t)d > (uintptr_t)s) while (size) { --size; d[size] = s[size]; }
    else for (size_t i = 0; i < size; ++i) d[i] = s[i];
    return to;
}
void *memset(void *to, int value, size_t size)
{ unsigned char *d = to; while (size--) *d++ = value; return to; }
int memcmp(const void *a, const void *b, size_t n)
{
    const unsigned char *x = a, *y = b;
    while (n--) { if (*x != *y) return *x - *y; ++x; ++y; }
    return 0;
}
void *memchr(const void *s, int c, size_t n)
{ const unsigned char *p = s; while (n--) { if (*p == (unsigned char)c) return (void *)p; ++p; } return NULL; }
size_t strlen(const char *s) { size_t n = 0; while (s[n]) ++n; return n; }
size_t strnlen(const char *s, size_t limit) { size_t n = 0; while (n < limit && s[n]) ++n; return n; }
int strcmp(const char *a, const char *b)
{ while (*a && *a == *b) { ++a; ++b; } return (unsigned char)*a - (unsigned char)*b; }
int strncmp(const char *a, const char *b, size_t n)
{ while (n && *a && *a == *b) { ++a; ++b; --n; } return n ? (unsigned char)*a - (unsigned char)*b : 0; }
char *strcpy(char *to, const char *from)
{ char *d = to; while ((*d++ = *from++)) {} return to; }
char *stpcpy(char *to, const char *from)
{ while ((*to = *from++)) ++to; return to; }
char *strncpy(char *to, const char *from, size_t n)
{ char *d = to; while (n && *from) { *d++ = *from++; --n; } while (n--) *d++ = 0; return to; }
char *strchr(const char *s, int c)
{ do { if (*s == (char)c) return (char *)s; } while (*s++); return NULL; }
char *strrchr(const char *s, int c)
{ const char *last = NULL; do { if (*s == (char)c) last = s; } while (*s++); return (char *)last; }

/* A coalescing metadata allocator. Haskell heap megablocks have a separate
 * allocator and are never taken from this fixed, kernel-owned arena. */
struct chunk { size_t size; struct chunk *next; uint32_t busy, tag; };
static unsigned char arena[8 * 1024 * 1024] __attribute__((aligned(16)));
static struct chunk *chunks;
#define TAG 0x484f5553u
void *malloc(size_t size)
{
    if (size > sizeof arena - 2 * sizeof(struct chunk)) { errno = ENOMEM; return NULL; }
    size = (size + 15) & ~(size_t)15;
    if (!size) size = 16;
    if (!chunks) {
        chunks = (void *)arena;
        *chunks = (struct chunk){sizeof arena - sizeof *chunks, NULL, 0, TAG};
    }
    for (struct chunk *p = chunks; p; p = p->next) {
        if (p->busy || p->size < size) continue;
        if (p->size >= size + sizeof *p + 16) {
            struct chunk *tail = (void *)((unsigned char *)(p + 1) + size);
            *tail = (struct chunk){p->size - size - sizeof *p, p->next, 0, TAG};
            p->size = size;
            p->next = tail;
        }
        p->busy = 1;
        return p + 1;
    }
    errno = ENOMEM;
    return NULL;
}
void free(void *pointer)
{
    if (!pointer) return;
    struct chunk *target = NULL;
    for (struct chunk *p = chunks; p; p = p->next) if (p + 1 == pointer) { target = p; break; }
    if (!target || target->tag != TAG || !target->busy) house_panic("invalid metadata free");
    target->busy = 0;
    for (struct chunk *p = chunks; p && p->next;) {
        if (!p->busy && !p->next->busy) {
            p->size += sizeof *p + p->next->size;
            p->next = p->next->next;
        } else p = p->next;
    }
}
void *calloc(size_t count, size_t size)
{
    if (size && count > SIZE_MAX / size) { errno = ENOMEM; return NULL; }
    size_t bytes = count * size;
    void *p = malloc(bytes);
    if (p) memset(p, 0, bytes);
    return p;
}
void *realloc(void *old, size_t size)
{
    if (!old) return malloc(size);
    if (!size) { free(old); return NULL; }
    struct chunk *p;
    for (p = chunks; p && p + 1 != old; p = p->next) {}
    if (!p || !p->busy) house_panic("invalid metadata realloc");
    void *fresh = malloc(size);
    if (fresh) { memcpy(fresh, old, size < p->size ? size : p->size); free(old); }
    return fresh;
}
char *strdup(const char *s)
{ size_t n = strlen(s) + 1; char *p = malloc(n); if (p) memcpy(p, s, n); return p; }

static void swap(unsigned char *a, unsigned char *b, size_t width)
{ while (width--) { unsigned char c = *a; *a++ = *b; *b++ = c; } }
static void sift(unsigned char *base, size_t root, size_t count, size_t width,
                 int (*compare)(const void *, const void *))
{
    while (root < count / 2) {
        size_t child = root * 2 + 1;
        if (child + 1 < count && compare(base + child * width, base + (child + 1) * width) < 0) ++child;
        if (compare(base + root * width, base + child * width) >= 0) return;
        swap(base + root * width, base + child * width, width); root = child;
    }
}
void qsort(void *array, size_t count, size_t width, int (*compare)(const void *, const void *))
{
    if (count < 2 || !width) return;
    if (count > SIZE_MAX / width) house_panic("invalid sort extent");
    unsigned char *base = array;
    for (size_t i = count / 2; i; --i) sift(base, i - 1, count, width, compare);
    for (size_t i = count - 1; i; --i) { swap(base, base + i * width, width); sift(base, 0, i, width, compare); }
}

static int error_number;
int *__errno_location(void) { return &error_number; }
void abort(void) { house_panic("abort"); }
void exit(int status) { house_test_exit(status != 0); }
void _exit(int status) { exit(status); }
void __assert_fail(const char *condition, const char *file, unsigned line, const char *function)
{ (void)file; (void)line; (void)function; house_panic(condition); }
char *getenv(const char *name) { (void)name; return NULL; } /* Empty environment. */

static FILE output_stream, error_stream;
FILE *stdout = &output_stream;
FILE *stderr = &error_stream;
static void valid_stream(FILE *stream)
{ if (stream != stdout && stream != stderr) house_panic("non-serial stdio stream"); }
size_t fwrite(const void *data, size_t size, size_t count, FILE *stream)
{
    valid_stream(stream);
    if (!size || !count) return 0;
    if (size && count > SIZE_MAX / size) return 0;
    const unsigned char *p = data;
    for (size_t i = 0; i < size * count; ++i) house_console_byte(p[i]);
    return count;
}
int fputc(int byte, FILE *stream)
{ valid_stream(stream); house_console_byte(byte); return (unsigned char)byte; }
int fputs(const char *text, FILE *stream) { return fwrite(text, 1, strlen(text), stream) == strlen(text) ? 0 : EOF; }
int puts(const char *text) { fputs(text, stdout); return fputc('\n', stdout); }
int fflush(FILE *stream)
{
    if (stream) valid_stream(stream);
    uint8_t status;
    do { __asm__ volatile("inb %1, %0" : "=a"(status) : "d"((uint16_t)0x3fd)); } while (!(status & 0x40));
    return 0;
}

struct text_buffer { char *data; size_t capacity, count; };
static void emit(struct text_buffer *b, char c)
{ if (b->count < b->capacity) b->data[b->count] = c; ++b->count; }
static void number(struct text_buffer *b, uint64_t value, unsigned base, int negative, int width, char fill)
{
    char digits[65]; unsigned used = 0;
    do { digits[used++] = "0123456789abcdef"[value % base]; value /= base; } while (value);
    if (negative && fill == '0') { emit(b, '-'); negative = 0; --width; }
    while (width-- > (int)used + negative) emit(b, fill);
    if (negative) emit(b, '-');
    while (used) emit(b, digits[--used]);
}
int vsnprintf(char *target, size_t capacity, const char *format, va_list arguments)
{
    struct text_buffer b = {target, capacity ? capacity - 1 : 0, 0};
    while (*format) {
        if (*format++ != '%') { emit(&b, format[-1]); continue; }
        if (*format == '%') { emit(&b, *format++); continue; }
        char fill = ' '; int width = 0, precision = -1, length = 0;
        while (*format == '-' || *format == '+' || *format == '#' || *format == ' ' || *format == '0')
            if (*format++ == '0') fill = '0';
        if (*format == '*') { width = va_arg(arguments, int); ++format; }
        else while (*format >= '0' && *format <= '9') width = width * 10 + *format++ - '0';
        if (*format == '.') {
            ++format; precision = 0;
            if (*format == '*') { precision = va_arg(arguments, int); ++format; }
            else while (*format >= '0' && *format <= '9') precision = precision * 10 + *format++ - '0';
        }
        if (*format == 'z') { length = 3; ++format; }
        else if (*format == 'l') { length = 1; if (*++format == 'l') { length = 2; ++format; } }
        char kind = *format++;
        if (kind == 's') {
            const char *s = va_arg(arguments, const char *); if (!s) s = "(null)";
            int n = precision; while (*s && n != 0) { emit(&b, *s++); if (n > 0) --n; }
        } else if (kind == 'c') emit(&b, va_arg(arguments, int));
        else if (kind == 'd' || kind == 'i') {
            int64_t value = length == 2 ? va_arg(arguments, long long) : length == 1 ? va_arg(arguments, long) :
                length == 3 ? va_arg(arguments, ptrdiff_t) : va_arg(arguments, int);
            number(&b, value < 0 ? -(uint64_t)value : (uint64_t)value, 10, value < 0, width, fill);
        } else if (kind == 'u' || kind == 'x' || kind == 'X' || kind == 'o' || kind == 'p') {
            uint64_t value = kind == 'p' ? (uintptr_t)va_arg(arguments, void *) :
                length == 2 ? va_arg(arguments, unsigned long long) : length == 1 ? va_arg(arguments, unsigned long) :
                length == 3 ? va_arg(arguments, size_t) : va_arg(arguments, unsigned);
            number(&b, value, kind == 'x' || kind == 'X' || kind == 'p' ? 16 : kind == 'o' ? 8 : 10, 0, width, fill);
        } else house_panic("unsupported diagnostic format");
    }
    if (capacity) target[b.count < capacity ? b.count : capacity - 1] = 0;
    return b.count;
}
int snprintf(char *target, size_t size, const char *format, ...)
{ va_list a; va_start(a, format); int n = vsnprintf(target, size, format, a); va_end(a); return n; }
int vfprintf(FILE *stream, const char *format, va_list a)
{
    char buffer[2048]; valid_stream(stream);
    int n = vsnprintf(buffer, sizeof buffer, format, a);
    fwrite(buffer, 1, strnlen(buffer, sizeof buffer), stream); return n;
}
int fprintf(FILE *stream, const char *format, ...)
{ va_list a; va_start(a, format); int n = vfprintf(stream, format, a); va_end(a); return n; }
int printf(const char *format, ...)
{ va_list a; va_start(a, format); int n = vfprintf(stdout, format, a); va_end(a); return n; }
