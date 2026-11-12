#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
exec python3 scripts/build-runtime.py "$@"
