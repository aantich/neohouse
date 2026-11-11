/* SPDX-License-Identifier: MIT */
#include "Rts.h"
#include "Capability.h"
#include "IOManagerInternals.h"
#include "Ticker.h"
#include "posix/Select.h"
#include "posix/Signals.h"
#include "platform.h"

int rts_stop_on_exception;
HsStablePtr rts_breakpoint_io_action;
KernelThreadId kernelThreadId(void) { return 0; } /* No host OS thread identity. */
unsigned int era;
StgWord user_era;
void heapCensus(Time time STG_UNUSED) { house_panic("heap profiling unavailable"); }

/* The collector uses only 2^x for its retained-memory decay. x87 provides the
 * required operation directly; a general libm pow API is not exposed. */
double house_pow2(double base, double exponent)
{
    if (base != 2.0) house_panic("unsupported collector exponentiation base");
    double result;
    __asm__ volatile (
        "fldl %1; fld %%st(0); frndint; fxch %%st(1); "
        "fsub %%st(1), %%st; f2xm1; fld1; faddp; fscale; "
        "fstp %%st(1); fstpl %0"
        : "=m"(result) : "m"(exponent) : "st", "st(1)");
    return result;
}

/* A static executable has no dynamically loaded object code for GC to mark. */
int n_unloaded_objects;
bool prepareUnloadCheck(void) { return false; }
void checkUnload(void) {}
void markObjectCode(const void *address STG_UNUSED) {}
void initUnloadCheck(void) {}
void exitUnloadCheck(void) {}
Capability *interpretBCO(Capability *cap STG_UNUSED)
{ house_panic("bytecode interpreter unavailable; compile native code"); }

/* Timer.c enforces tickInterval == 0. Unexpected attempts to enable the OS
 * ticker are fatal; no fabricated timer delivery or pthread implementation. */
void initTicker(Time interval STG_UNUSED, TickProc callback STG_UNUSED)
{ house_panic("interrupt ticker unavailable"); }
void startTicker(void) { house_panic("interrupt ticker unavailable"); }
void stopTicker(void) { house_panic("interrupt ticker unavailable"); }
void exitTicker(bool wait STG_UNUSED) { house_panic("interrupt ticker unavailable"); }

/* The scheduler may poll empty queues. Blocking on a Unix FD or an RTS
 * delay is unsupported; UART input uses an explicit polling device API. */
void awaitCompletedTimeoutsOrIOSelect(Capability *cap, bool wait)
{
    if (wait || cap->iomgr->blocked_queue_hd != END_TSO_QUEUE ||
        cap->iomgr->sleeping_queue != END_TSO_QUEUE)
        house_panic("Unix I/O waits and delays unavailable");
}
LowResTime getDelayTarget(HsInt delay STG_UNUSED)
{ house_panic("RTS delays unavailable"); }

/* No Unix signal source exists and installation is disabled before scheduling.
 * The scheduler's pending-signal check must always see an empty buffer. */
siginfo_t pending_handler_buf[1];
siginfo_t *next_pending_handler = pending_handler_buf;
StgInt *signal_handlers;
bool anyUserHandlers(void) { return false; }
void blockUserSignals(void) {}
void unblockUserSignals(void) {}
void startSignalHandlers(Capability *cap STG_UNUSED)
{ house_panic("Unix signals unavailable"); }
void awaitUserSignals(void) { house_panic("Unix signals unavailable"); }
void ioManagerWakeup(void) { house_panic("Unix I/O manager unavailable"); }
