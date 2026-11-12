-- SPDX-License-Identifier: MIT
module HouseSubmission (submission) where

import House

twice :: Num a => a -> a
twice x = x + x

submission :: OS ()
submission = do
    writeLine console "Hello from an ordinary Haskell module"
    printValue console (twice (21 :: Int))
    printValue console (map twice [1 .. 5 :: Int])
    printValue console ((2 :: Integer) ^ (200 :: Int))
    snapshot <- memoryInfo
    printValue console snapshot
    result <- attempt (evaluate (7 `div` (0 :: Int)))
    case result of
        Left message -> writeLine console ("Recovered: " ++ message)
        Right value -> printValue console value
    writeLine console "The guest is still running after that exception"
