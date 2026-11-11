-- SPDX-License-Identifier: MIT
{-# LANGUAGE MagicHash, NoImplicitPrelude, UnboxedTuples #-}
module HouseCallbacks (runIO, runNonIO, runMainIO, flushStdHandles, unsupported) where

import GHC.Internal.Types (IO(..))
import GHC.Exts (runRW#, unsafeCoerce#)

foreign import ccall unsafe "house_unsupported_callback" die :: IO ()

-- Raw rts_evalIO entry owns the final scheduler status. There are no Unix
-- standard handles or process-level main-thread handlers in this checkpoint.
runIO :: IO a -> IO a
runIO action = action

runMainIO :: IO a -> IO a
runMainIO action = action

runNonIO :: a -> IO a
runNonIO value = IO (\state -> (# state, value #))

flushStdHandles :: IO ()
flushStdHandles = IO (\state -> (# state, () #))

-- A callback belonging to an unavailable platform feature must never return.
-- This closure can be entered at any expected type because die halts the VM.
{-# NOINLINE unsupported #-}
unsupported :: a
unsupported = case die of
    IO action -> runRW# (\state -> case action state of (# _, value #) -> unsafeCoerce# value)
