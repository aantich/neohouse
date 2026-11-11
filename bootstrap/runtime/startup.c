/* SPDX-License-Identifier: MIT
 * Single-capability, statically linked runtime initialization using the
 * interfaces of the pinned GHC release. Dynamic loading, Unix handles,
 * signals, coverage files and asynchronous tick delivery are unavailable.
 */
#include "Rts.h"
#include "RtsFlags.h"
#include "Stats.h"
#include "Schedule.h"
#include "BuiltinClosures.h"
#include "sm/Storage.h"
#include "StablePtr.h"
#include "StableName.h"
#include "ForeignExports.h"
#include "TopHandler.h"
#include "Globals.h"
#include "IPE.h"
#include "ProfHeap.h"
#include "Timer.h"
#include "IOManager.h"
#include "CheckVectorSupport.h"
#include "hooks/Hooks.h"
#include "platform.h"

void init_ghc_hs_iface(void);

void house_rts_init(void)
{
    init_ghc_hs_iface();
    initStats0();
    initializeTimer();
    stat_startInit();
    initRtsFlagsDefaults();
    RtsFlags.MiscFlags.install_signal_handlers = false;
    RtsFlags.MiscFlags.tickInterval = 0;
    RtsFlags.ConcFlags.ctxtSwitchTime = 0;
    RtsFlags.ConcFlags.ctxtSwitchTicks = 0;
    RtsFlags.GcFlags.doIdleGC = false;
    RtsFlags.GcFlags.giveStats = COLLECT_GC_STATS;
    RtsFlags.GcFlags.maxHeapSize = (128 * 1024 * 1024) / BLOCK_SIZE;
    RtsFlags.GcFlags.largeAllocLim = RtsFlags.GcFlags.minAllocAreaSize;
    RtsFlags.HpcFlags.readTixFile = HPC_NO_EXPLICIT;
    RtsFlags.HpcFlags.writeTixFile = false;
    rtsConfig = (RtsConfig) {
        .rts_opts_enabled = RtsOptsNone,
        .onExitHook = OnExitHook,
        .stackOverflowHook = StackOverflowHook,
        .outOfHeapHook = OutOfHeapHook,
        .mallocFailHook = MallocFailHook,
        .longGCSync = LongGCSync,
        .longGCSyncEnd = LongGCSyncEnd
    };
    prog_name = "house";
    selectIOManager();
    setVectorSupport();
    initStats1();
    initTimer();
    house_message("RTS scheduler initialization\r\n");
    initScheduler();
    initBuiltinClosures();
    house_message("RTS storage initialization\r\n");
    initStorage();
    initStablePtrTable();
    initStableNameTable();
#define CLOSURE(module, symbol) getStablePtr((StgPtr)ghc_hs_iface->symbol);
#define UNDEF_CLOSURE(module, symbol)
#define INFO_TBL(module, symbol)
#include "RtsIfaceSymbols.h"
#undef CLOSURE
#undef UNDEF_CLOSURE
#undef INFO_TBL
    processForeignExports();
    initTopHandler();
    initGlobalStore();
    initIpe();
    startTimer();
    initIOManager();
    stat_endInit();
}

void stg_exit(int status) { house_test_exit(status != 0); }
void shutdownHaskellAndExit(int status, int fast_exit STG_UNUSED) { stg_exit(status); }
void hs_exit(void) { house_panic("hs_exit is not supported by this checkpoint"); }
void hs_exit_nowait(void) { hs_exit(); }
