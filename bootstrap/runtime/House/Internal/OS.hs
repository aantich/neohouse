-- SPDX-License-Identifier: MIT
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
module House.Internal.OS (OS(..)) where

-- This is an effect interface for the trusted prototype, not isolation.
-- Keep the constructor out of the public House module.
newtype OS a = OS { runOS :: IO a }
    deriving (Functor, Applicative, Monad)
