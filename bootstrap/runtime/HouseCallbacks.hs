-- SPDX-License-Identifier: MIT
{-# LANGUAGE MagicHash, NoImplicitPrelude, UnboxedTuples #-}
module HouseCallbacks (runIO, runNonIO, runMainIO, flushStdHandles, unsupported) where

import GHC.Internal.Types (IO(..), Int(..))
import GHC.Internal.Magic (runRW#)
import GHC.Internal.IO (catch, evaluate)
import GHC.Internal.Exception.Type (SomeException, displayException)
import HouseIO
import Serial (serial)

foreign import ccall unsafe "house_unsupported_callback" die :: IO ()
foreign import ccall unsafe "house_test_exit" testExit :: Int -> IO ()

-- There are no Unix standard handles or process-level main-thread handlers.
-- An uncaught exception at a C/RTS boundary is a visible kernel failure;
-- recoverable evaluation must install its handler inside that boundary.
runIO :: IO a -> IO a
runIO action = catch action fatal

fatal :: SomeException -> IO a
fatal exception = serial "Uncaught Haskell exception: " >>
    serial (displayException exception) >> serial "\r\n" >> testExit (I# 1#) >> fatal exception

runMainIO :: IO a -> IO a
runMainIO = runIO

runNonIO :: a -> IO a
runNonIO value = runIO (evaluate value)

flushStdHandles :: IO ()
flushStdHandles = IO (\state -> (# state, () #))

-- A callback belonging to an unavailable platform feature must never return.
-- This closure can be entered at any expected type because die halts the VM.
{-# NOINLINE unsupported #-}
unsupported :: a
unsupported = case die of
    IO action -> runRW# (\state -> case action state of (# _, () #) -> unsupported)
