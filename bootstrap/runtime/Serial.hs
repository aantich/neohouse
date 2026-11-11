-- SPDX-License-Identifier: MIT
{-# LANGUAGE MagicHash, NoImplicitPrelude #-}
module Serial (serial, putByte, getByte) where
import GHC.Internal.Types (Char(..), Int(..), IO)
import GHC.Internal.Prim
import HouseIO

foreign import ccall unsafe "house_in8" in8 :: Int -> IO Int
foreign import ccall unsafe "house_out8" out8 :: Int -> Int -> IO ()

-- Device policy and polling are Haskell. The FFI wrappers contain only the
-- CPU port-I/O instructions. COM1 was configured by the early boot entry.
putByte :: Int# -> IO ()
putByte byte = do
    I# status <- in8 (I# 1021#)
    case andI# status 32# ==# 0# of
        1# -> putByte byte
        _ -> out8 (I# 1016#) (I# byte)

getByte :: IO Int
getByte = do
    I# status <- in8 (I# 1021#)
    case andI# status 1# ==# 0# of
        1# -> getByte
        _ -> in8 (I# 1016#)

serial :: [Char] -> IO ()
serial [] = pure ()
serial (C# char : rest) = putByte (ord# char) >> serial rest
