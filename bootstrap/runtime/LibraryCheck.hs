-- SPDX-License-Identifier: MIT
-- Deliberately exercise Prelude's partial head to test exception recovery.
{-# OPTIONS_GHC -Wno-x-partial #-}
module LibraryCheck (runLibraryCheck) where

import Data.IORef
import Data.List (isInfixOf)
import qualified Control.Exception as Exception
import Foreign.C.Error (eNOMEM, errnoToIOError, getErrno, resetErrno)
import Foreign.Marshal.Alloc (mallocBytes)
import Foreign.Ptr (Ptr)
import Foreign.C.String (peekCString, withCString)
import GHC.Internal.Bignum.Backend (backendName)
import GHC.Internal.Exception.Backtrace (BacktraceMechanism(IPEBacktrace), setBacktraceMechanismState)
import GHC.Internal.Fingerprint (getFileHash)
import GHC.Internal.IO.Encoding (mkTextEncoding)
import House
import House.Internal.OS (OS(..))

-- Prevent the compiler from precomputing the test inputs and large-number
-- arithmetic. All these operations must actually execute in the guest.
{-# OPAQUE input #-}
input :: a -> a
input value = value

data Sample = Sample Int Bool [Int] deriving (Eq, Show)

ensure :: String -> Bool -> OS ()
ensure name condition = if condition then pure () else error ("Library check failed: " ++ name)

expectException :: String -> String -> OS a -> OS ()
expectException name message action = do
    result <- attempt action
    case result of
        Left diagnostic -> ensure (name ++ " diagnostic") (message `isInfixOf` diagnostic)
        Right _ -> error ("Library check failed: no exception for " ++ name)

runLibraryCheck :: IO ()
runLibraryCheck = runOS $ do
    ensure "native backend" (backendName == "native")
    let twice x = x + x
    ensure "polymorphic function" (twice (input 21 :: Int) == 42)
    ensure "list pipeline" (sum (map (twice . (+ 1)) (filter even [input 1 .. 10 :: Int])) == 70)
    ensure "signed Int display" (show (input minBound :: Int) == "-2147483648")
    ensure "derived Show" (show (Sample (-3) True [1,2]) == "Sample (-3) True [1,2]")
    let big = (2 :: Integer) ^ (input 200 :: Int)
        factorial = product [1 .. input 100] :: Integer
        factor = input 4294967297 :: Integer
        dividend = big * factor + 123
    ensure "multiword multiply/divide" (dividend `quotRem` factor == (big, 123))
    ensure "negative division" ((negate dividend) `divMod` factor == (negate big - 1, factor - 123))
    ensure "factorial rendering" (show factorial ==
        "93326215443944152681699238856266700490715968264381621468592963895217599993229915608941463976156518286253697920827223758251185210916864000000000000000000000000")
    root <- OS (newIORef (big, factorial))
    collect
    (moved, retainedFactorial) <- OS (readIORef root)
    ensure "Integer retained across GC" (show moved ==
        "1606938044258990275541962092341162602522202993782792835301376")
    ensure "second retained Integer" (retainedFactorial `mod` factor == 4068283320)
    writeLine console "Haskell values passed: functions, lists, Show, native Integer, retained GC roots"
    expectException "division by zero" "divide by zero" (evaluate (input 7 `div` input 0 :: Int))
    expectException "Integer division by zero" "divide by zero" (evaluate (big `quot` input 0))
    expectException "error" "deliberate evaluation failure" (evaluate (error "deliberate evaluation failure" :: Int))
    expectException "partial list" "empty list" (evaluate (head (input [] :: [Int])))
    expectException "lazy rendering" "lazy value failed"
        (evaluate (length (show [input 1, error "lazy value failed" :: Int])))
    OS resetErrno
    expectException "metadata allocation failure" "out of memory"
        (OS (mallocBytes (input maxBound) :: IO (Ptr ())))
    allocationError <- OS getErrno
    ensure "allocator errno" (allocationError == eNOMEM)
    expectException "errno conversion" "House errno 12"
        (OS (Exception.throwIO (errnoToIOError "metadata allocator" allocationError Nothing Nothing)))
    typed <- OS (Exception.try (Exception.evaluate (input 9 `div` input 0 :: Int))
                 :: IO (Either Exception.ArithException Int))
    case typed of
        Left Exception.DivideByZero -> pure ()
        _ -> error "Library check failed: typed arithmetic exception"
    decoded <- OS (withCString "lambda: \955" peekCString)
    ensure "Haskell UTF-8 codec round trip" (decoded == "lambda: \955")
    expectException "unsupported codec" "unknown encoding" (OS (mkTextEncoding "SHIFT-JIS"))
    expectException "file hashing" "file hashing unavailable" (OS (getFileHash "unavailable-file"))
    expectException "IPE backtrace" "IPE backtraces unavailable"
        (OS (setBacktraceMechanismState IPEBacktrace True))
    -- Rejected configuration must leave normal exception collection usable.
    expectException "exception after rejected IPE option" "normal exception still works"
        (evaluate (error "normal exception still works" :: Int))
    -- A subsequent evaluation must succeed on the same Haskell thread.
    answer <- evaluate (twice (input 21 :: Int))
    ensure "recovery" (answer == 42)
    collect
    writeLine console "Haskell exceptions passed: Int/Integer division, error, partial list, lazy rendering, allocator failure; recovered=42"
    writeLine console "Haskell platform boundary passed: typed exceptions, UTF-8, unsupported codec/file hash/IPE rejection"
    writeLine console "Standalone Haskell library checkpoint passed; bignum_backend=native"
