-- SPDX-License-Identifier: MIT
{-# LANGUAGE NoImplicitPrelude, UnboxedTuples #-}
module HouseIO ((>>=), (>>), pure) where
import GHC.Internal.Types (IO(..))

infixl 1 >>=, >>
(>>=) :: IO a -> (a -> IO b) -> IO b
IO first >>= next = IO (\state -> case first state of
    (# state', value #) -> case next value of IO second -> second state')
(>>) :: IO a -> IO b -> IO b
first >> second = first >>= \_ -> second
pure :: a -> IO a
pure value = IO (\state -> (# state, value #))
