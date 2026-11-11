/* SPDX-License-Identifier: MIT */
#include "Rts.h"
#include "GetTime.h"
#include "platform.h"

/* QEMU's PC HPET. No interrupts are enabled; only its free-running counter is
 * used. The platform test rejects machines without the 64-bit counter. */
static volatile uint32_t *const hpet = (void *)0xfed00000;
static uint32_t period_fs;

void initializeTimer(void)
{
    uint32_t capabilities = hpet[0];
    period_fs = hpet[1];
    if (capabilities == UINT32_MAX || !(capabilities & (1u << 13)) ||
        !period_fs || period_fs > 100000000)
        house_panic("64-bit HPET clock required");
    hpet[0x10 / 4] = 0;
    hpet[0xf0 / 4] = 0;
    hpet[0xf4 / 4] = 0;
    hpet[0x10 / 4] = 1;
    StgWord64 initial = getMonotonicNSec();
    for (unsigned i = 0; i < 100000; ++i)
        if (getMonotonicNSec() > initial) return;
    house_panic("HPET counter did not advance");
}

StgWord64 getMonotonicNSec(void)
{
    uint32_t high, low, again;
    do {
        high = hpet[0xf4 / 4];
        low = hpet[0xf0 / 4];
        again = hpet[0xf4 / 4];
    } while (high != again);
    uint64_t ticks = ((uint64_t)high << 32) | low;
    return (ticks / 1000000) * period_fs + (ticks % 1000000) * period_fs / 1000000;
}

Time getProcessElapsedTime(void) { return NSToTime(getMonotonicNSec()); }
/* One active CPU, no sleeping and no other guest processes in this checkpoint. */
Time getProcessCPUTime(void) { return getProcessElapsedTime(); }
Time getCurrentThreadCPUTime(void) { return getProcessElapsedTime(); }
void getProcessTimes(Time *user, Time *elapsed)
{ *user = *elapsed = getProcessElapsedTime(); }
W_ getPageFaults(void) { return 0; } /* Paging is disabled. */
void getUnixEpochTime(StgWord64 *seconds STG_UNUSED, StgWord32 *nanos STG_UNUSED)
{ house_panic("wall clock not implemented"); }
