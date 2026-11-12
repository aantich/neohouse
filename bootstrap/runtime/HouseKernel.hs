-- SPDX-License-Identifier: MIT
{-# LANGUAGE CPP, MagicHash, NoImplicitPrelude, UnboxedTuples #-}
module HouseKernel (entry) where

import GHC.Internal.Types (Char(..), Int(..), IO(..))
import GHC.Internal.Prim
import qualified HouseCallbacks
import HouseIO
import Serial
import LibraryCheck (runLibraryCheck)
#ifdef HOUSE_SUBMISSION
import SubmissionRunner (runSubmission)
#endif

foreign import ccall unsafe "house_test_exit" testExit :: Int -> IO ()
foreign import ccall safe "performMajorGC" majorGC :: IO ()
foreign import ccall unsafe "house_gc_count" gcCount :: IO Int
foreign import ccall unsafe "house_allocated_bytes" allocatedBytes :: IO Int

data Chain = End | Link Int# Chain
data Root = Root (MutVar# RealWorld Chain)

newRoot :: IO Root
newRoot = IO (\state -> case newMutVar# End state of
    (# state', root #) -> (# state', Root root #))
readRoot :: Root -> IO Chain
readRoot (Root root) = IO (\state -> readMutVar# root state)
writeRoot :: Root -> Chain -> IO ()
writeRoot (Root root) value = IO (\state -> case writeMutVar# root value state of
    state' -> (# state', () #))

{-# NOINLINE makeChain #-}
makeChain :: Int# -> Int# -> Chain
makeChain 0# _ = End
makeChain count seed = Link (count +# seed) (makeChain (count -# 1#) seed)

{-# NOINLINE checksum #-}
checksum :: Chain -> Int#
checksum = go 0#
  where
    go total End = total
    go total (Link value rest) = go (total +# value) rest

check :: Int# -> Int# -> [Char] -> IO ()
check actual expected message = case actual ==# expected of
    1# -> pure ()
    _ -> serial "FAIL: " >> serial message >> serial "\r\n" >> testExit (I# 1#)

decimal :: Int# -> [Char]
decimal value = go value []
  where
    go n tail = case n <# 10# of
        1# -> C# (chr# (48# +# n)) : tail
        _ -> go (quotInt# n 10#) (C# (chr# (48# +# remInt# n 10#)) : tail)

rounds :: Root -> Int# -> IO ()
rounds root seed = case seed ># 12# of
    1# -> pure ()
    _ -> do
        writeRoot root (makeChain 50000# seed)
        live <- readRoot root
        let expected = 1250025000# +# 50000# *# seed
        check (checksum live) expected "checksum before GC"
        majorGC
        moved <- readRoot root
        check (checksum moved) expected "live root corrupted by GC"
        writeRoot root End
        majorGC
        rounds root (seed +# 1#)

runGCCheck :: IO ()
runGCCheck = do
    I# before <- gcCount
    I# allocatedBefore <- allocatedBytes
    root <- newRoot
    rounds root 1#
    I# after <- gcCount
    I# allocatedAfter <- allocatedBytes
    let collections = after -# before
        allocated = allocatedAfter -# allocatedBefore
    check (collections >=# 24#) 1# "collection count"
    check (allocated ># 1000000#) 1# "allocation count"
    serial "Standalone Haskell GC checkpoint passed; collections="
    serial (decimal collections)
    serial "; allocated_bytes="
    serial (decimal allocated)
    serial "\r\n"

foreign import ccall unsafe "house_interactive" interactive :: IO Int
foreign import ccall unsafe "house_heap_capacity_mb" heapCapacity :: IO Int
foreign import ccall unsafe "house_mblocks_in_use" heapInUse :: IO Int

data Line = Line [Char] Int#

reverse :: [a] -> [a]
reverse input = go input []
  where
    go [] output = output
    go (x:xs) output = go xs (x:output)

-- Bounded ASCII editing. Ignore escape sequences (for example arrow keys),
-- recognize CR/LF/CRLF, support backspace/delete, Ctrl-U and Ctrl-C.
readLine :: Int# -> IO Line
readLine previousCR = go [] 0# previousCR
  where
    go chars count skipLF = do
        I# byte <- getByte
        case byte of
            13# -> serial "\r\n" >> pure (Line (reverse chars) 1#)
            10# -> case skipLF of
                1# -> go chars count 0#
                _ -> serial "\r\n" >> pure (Line (reverse chars) 0#)
            8# -> erase chars count
            127# -> erase chars count
            21# -> clearLine count >> go [] 0# 0#
            3# -> serial "^C\r\n" >> pure (Line [] 0#)
            27# -> escape 0# >> go chars count 0#
            _ -> case (byte >=# 32#) *# (byte <=# 126#) *# (count <# 256#) of
                1# -> putByte byte >> go (C# (chr# byte):chars) (count +# 1#) 0#
                _ -> go chars count 0#
    erase [] count = go [] count 0#
    erase (_:rest) count = serial "\b \b" >> go rest (count -# 1#) 0#
    clearLine 0# = pure ()
    clearLine count = serial "\b \b" >> clearLine (count -# 1#)
    escape count = do
        I# byte <- getByte
        case count ==# 0# of
            1# -> case byte ==# 91# of 1# -> escape 1#; _ -> pure ()
            _ -> case (byte >=# 64#) *# (byte <=# 126#) of
                1# -> pure ()
                _ -> case count <# 16# of 1# -> escape (count +# 1#); _ -> pure ()

equal :: [Char] -> [Char] -> Int#
equal [] [] = 1#
equal (C# a:as) (C# b:bs) = case eqChar# a b of 1# -> equal as bs; _ -> 0#
equal _ _ = 0#

data Prefix = Missing | Rest [Char]
strip :: [Char] -> [Char] -> Prefix
strip [] value = Rest value
strip (C# a:as) (C# b:bs) = case eqChar# a b of 1# -> strip as bs; _ -> Missing
strip _ _ = Missing

memoryInfo :: IO ()
memoryInfo = do
    I# capacity <- heapCapacity
    I# used <- heapInUse
    I# collections <- gcCount
    serial "Heap capacity: " >> serial (decimal capacity) >> serial " MiB; acquired: "
    serial (decimal used) >> serial " MiB; collections: "
    serial (decimal collections) >> serial "\r\n"

shell :: Int# -> IO ()
shell previousCR = do
    serial "house> "
    Line command cr <- readLine previousCR
    case equal command "halt" of
        1# -> serial "House halted\r\n"
        _ -> execute command >> shell cr
  where
    execute [] = pure ()
    execute command = case equal command "help" of
        1# -> serial "help  mem  gc  selftest  echo TEXT  clear  halt\r\n"
        _ -> case equal command "mem" of
            1# -> memoryInfo
            _ -> case equal command "gc" of
                1# -> majorGC >> serial "Major GC completed\r\n" >> memoryInfo
                _ -> case equal command "selftest" of
                    1# -> runGCCheck
                    _ -> case equal command "clear" of
                        1# -> serial "\ESC[2J\ESC[H"
                        _ -> case strip "echo " command of
                            Rest text -> serial text >> serial "\r\n"
                            Missing -> serial "Unknown command; type help\r\n"

entry :: IO ()
entry = HouseCallbacks.runIO boot

boot :: IO ()
boot = do
    serial "Entered native Haskell (GHC 9.14.1)\r\n"
    runGCCheck
    runLibraryCheck
#ifdef HOUSE_SUBMISSION
    runSubmission
#endif
    I# enabled <- interactive
    case enabled of
        0# -> pure ()
        _ -> serial "House serial terminal ready. Type help.\r\n" >> shell 0#
