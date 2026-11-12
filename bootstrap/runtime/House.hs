-- SPDX-License-Identifier: MIT
module House
    ( OS, Console, console, writeLine, printValue
    , MemoryInfo(..), memoryInfo, collect, evaluate, attempt
    ) where

import qualified Control.Exception as Exception
import House.Internal.OS (OS(..))
import Serial (serial)

-- Only the kernel grants this handle. There is no raw port/address in its
-- public interface. The current guest still executes trusted kernel code.
data Console = Console

console :: Console
console = Console

writeLine :: Console -> String -> OS ()
writeLine Console text = OS (serial text >> serial "\r\n")

printValue :: Show a => Console -> a -> OS ()
printValue output value = writeLine output (show value)

data MemoryInfo = MemoryInfo
    { heapBytes :: Int
    , usableBytes :: Int
    , collections :: Int
    } deriving (Eq, Show)

foreign import ccall unsafe "house_heap_capacity_mb" capacityMiB :: IO Int
foreign import ccall unsafe "house_mblocks_in_use" acquiredMiB :: IO Int
foreign import ccall unsafe "house_gc_count" gcCount :: IO Int
foreign import ccall safe "performMajorGC" majorGC :: IO ()

-- An immutable snapshot; subsequent allocation does not update this value.
memoryInfo :: OS MemoryInfo
memoryInfo = OS $ do
    used <- acquiredMiB
    capacity <- capacityMiB
    count <- gcCount
    pure (MemoryInfo (used * 1048576) (capacity * 1048576) count)

collect :: OS ()
collect = OS majorGC

-- As with Control.Exception.evaluate, this forces only weak head normal form.
evaluate :: a -> OS a
evaluate value = OS (Exception.evaluate value)

-- Catch exceptions raised while the action runs, including while its output
-- is rendered. Lazy results can still throw when demanded outside this action.
-- Performed device I/O is not rolled back.
attempt :: OS a -> OS (Either String a)
attempt (OS action) = OS $ do
    result <- Exception.try action
    pure $ case result of
        Left exception -> Left (Exception.displayException (exception :: Exception.SomeException))
        Right value -> Right value
