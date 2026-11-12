-- SPDX-License-Identifier: MIT
module SubmissionRunner (runSubmission) where

import House
import House.Internal.OS (OS(..))
import qualified HouseSubmission

foreign import ccall unsafe "house_test_exit" testExit :: Int -> IO ()

runSubmission :: IO ()
runSubmission = runOS $ do
    writeLine console "Running host-compiled native Haskell submission inside House"
    result <- attempt HouseSubmission.submission
    case result of
        Left diagnostic -> do
            writeLine console ("Submission failed: " ++ diagnostic)
            OS (testExit 1)
        Right () -> writeLine console "Native Haskell submission completed"
