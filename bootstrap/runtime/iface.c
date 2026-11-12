/* SPDX-License-Identifier: MIT
 * Restricted RTS/Haskell interface for the first boot. Primitive boxed
 * types and exception values come from the source-built guest library.
 * Unix I/O and other unavailable callbacks enter a fatal diagnostic closure.
 */
#include "Rts.h"
extern StgClosure HouseCallbacks_unsupported_closure;
extern StgClosure HouseCallbacks_runIO_closure, HouseCallbacks_runNonIO_closure;
extern StgClosure HouseCallbacks_runMainIO_closure, HouseCallbacks_flushStdHandles_closure;
extern StgClosure ghczminternal_GHCziInternalziTuple_Z0T_closure;
extern StgClosure ghczminternal_GHCziInternalziTypes_True_closure;
extern StgClosure ghczminternal_GHCziInternalziTypes_False_closure;
#define BASIC_INFO(name) extern const StgInfoTable ghczminternal_GHCziInternalziTypes_##name
BASIC_INFO(Czh_con_info); BASIC_INFO(Izh_con_info); BASIC_INFO(Wzh_con_info);
BASIC_INFO(Fzh_con_info); BASIC_INFO(Dzh_con_info);
#undef BASIC_INFO
extern const StgInfoTable ghczminternal_GHCziInternalziCString_unpackCStringzh_info;
extern const StgInfoTable ghczminternal_GHCziInternalziCString_unpackCStringUtf8zh_info;

#define EXCEPTION(module, symbol) extern StgClosure ghczminternal_##module##_##symbol
EXCEPTION(GHCziInternalziExceptionziType, divZZeroException_closure);
EXCEPTION(GHCziInternalziExceptionziType, underflowException_closure);
EXCEPTION(GHCziInternalziExceptionziType, overflowException_closure);
EXCEPTION(GHCziInternalziIOziException, stackOverflow_closure);
EXCEPTION(GHCziInternalziIOziException, heapOverflow_closure);
EXCEPTION(GHCziInternalziIOziException, allocationLimitExceeded_closure);
EXCEPTION(GHCziInternalziIOziException, blockedIndefinitelyOnMVar_closure);
EXCEPTION(GHCziInternalziIOziException, blockedIndefinitelyOnSTM_closure);
EXCEPTION(GHCziInternalziIOziException, cannotCompactFunction_closure);
EXCEPTION(GHCziInternalziIOziException, cannotCompactPinned_closure);
EXCEPTION(GHCziInternalziIOziException, cannotCompactMutable_closure);
EXCEPTION(GHCziInternalziControlziExceptionziBase, nonTermination_closure);
EXCEPTION(GHCziInternalziControlziExceptionziBase, nestedAtomically_closure);
EXCEPTION(GHCziInternalziControlziExceptionziBase, noMatchingContinuationPrompt_closure);
#undef EXCEPTION

static HsIface interface;
void init_ghc_hs_iface(void)
{
    /* Unused boxing info tables remain NULL. Their C API entry points are
     * removed by section GC and are not exposed by this Haskell program. */
#define CLOSURE(module, symbol) interface.symbol = &HouseCallbacks_unsupported_closure;
#define UNDEF_CLOSURE(module, symbol)
#define INFO_TBL(module, symbol)
#include "RtsIfaceSymbols.h"
#undef CLOSURE
#undef UNDEF_CLOSURE
#undef INFO_TBL
    interface.runIO_closure = &HouseCallbacks_runIO_closure;
    interface.runNonIO_closure = &HouseCallbacks_runNonIO_closure;
    interface.runMainIO_closure = &HouseCallbacks_runMainIO_closure;
    interface.flushStdHandles_closure = &HouseCallbacks_flushStdHandles_closure;
    interface.Z0T_closure = &ghczminternal_GHCziInternalziTuple_Z0T_closure;
    interface.True_closure = &ghczminternal_GHCziInternalziTypes_True_closure;
    interface.False_closure = &ghczminternal_GHCziInternalziTypes_False_closure;
#define BASIC_INFO(name) interface.name = &ghczminternal_GHCziInternalziTypes_##name
    BASIC_INFO(Czh_con_info); BASIC_INFO(Izh_con_info); BASIC_INFO(Wzh_con_info);
    BASIC_INFO(Fzh_con_info); BASIC_INFO(Dzh_con_info);
#undef BASIC_INFO
    interface.unpackCStringzh_info = &ghczminternal_GHCziInternalziCString_unpackCStringzh_info;
    interface.unpackCStringUtf8zh_info = &ghczminternal_GHCziInternalziCString_unpackCStringUtf8zh_info;
#define EXCEPTION(module, symbol) interface.symbol = &ghczminternal_##module##_##symbol
    EXCEPTION(GHCziInternalziExceptionziType, divZZeroException_closure);
    EXCEPTION(GHCziInternalziExceptionziType, underflowException_closure);
    EXCEPTION(GHCziInternalziExceptionziType, overflowException_closure);
    EXCEPTION(GHCziInternalziIOziException, stackOverflow_closure);
    EXCEPTION(GHCziInternalziIOziException, heapOverflow_closure);
    EXCEPTION(GHCziInternalziIOziException, allocationLimitExceeded_closure);
    EXCEPTION(GHCziInternalziIOziException, blockedIndefinitelyOnMVar_closure);
    EXCEPTION(GHCziInternalziIOziException, blockedIndefinitelyOnSTM_closure);
    EXCEPTION(GHCziInternalziIOziException, cannotCompactFunction_closure);
    EXCEPTION(GHCziInternalziIOziException, cannotCompactPinned_closure);
    EXCEPTION(GHCziInternalziIOziException, cannotCompactMutable_closure);
    EXCEPTION(GHCziInternalziControlziExceptionziBase, nonTermination_closure);
    EXCEPTION(GHCziInternalziControlziExceptionziBase, nestedAtomically_closure);
    EXCEPTION(GHCziInternalziControlziExceptionziBase, noMatchingContinuationPrompt_closure);
#undef EXCEPTION
    ghc_hs_iface = &interface;
}
