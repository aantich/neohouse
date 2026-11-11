-- SPDX-License-Identifier: MIT
{-# LANGUAGE BangPatterns #-}
module Main (main) where

import Control.Exception (evaluate)
import Control.Monad (forM_, unless)
import Data.IORef (newIORef, readIORef, writeIORef)
import Data.Word (Word32)
import Foreign.Storable (sizeOf)
import GHC.Stats (RTSStats(..), getRTSStats, getRTSStatsEnabled)
import System.Mem (performMajorGC)

data Chain = End | Link !Word32 Chain

{-# NOINLINE makeChain #-}
makeChain :: Word32 -> Word32 -> Chain
makeChain 0 _ = End
makeChain n seed = Link (seed + n) (makeChain (n - 1) seed)

{-# NOINLINE checksum #-}
checksum :: Chain -> Word32
checksum = go 0
  where
    go !total End = total
    go !total (Link x rest) = go (total + x) rest

main :: IO ()
main = do
    unless (sizeOf (0 :: Int) == 4) $ fail "Expected an IA32 executable"
    enabled <- getRTSStatsEnabled
    unless enabled $ fail "RTS statistics must be enabled with +RTS -T"
    before <- getRTSStats
    root <- newIORef End
    let count = 50000 :: Word32
    forM_ [1..12] $ \seed -> do
        writeIORef root (makeChain count seed)
        chain <- readIORef root
        result <- evaluate (checksum chain)
        let expected = count * seed + (count `div` 2) * (count + 1)
        unless (result == expected) $ fail "Checksum before collection failed"
        performMajorGC
        surviving <- readIORef root
        afterGC <- evaluate (checksum surviving)
        unless (afterGC == expected) $ fail "Live chain corrupted during collection"
        writeIORef root End
        performMajorGC
    after <- getRTSStats
    let collections = gcs after - gcs before
        allocated = allocated_bytes after - allocated_bytes before
    unless (collections >= 24 && allocated > 1000000) $
        fail "Allocation/collection checkpoint was not exercised"
    putStrLn "Hosted IA32 native-code checkpoint passed"
    putStrLn $ "Collections: " ++ show collections
    putStrLn $ "Allocated bytes: " ++ show allocated
    putStrLn $ "Maximum live bytes: " ++ show (max_live_bytes after)
    putStrLn "This verifies the hosted toolchain; standalone boot remains separate."
