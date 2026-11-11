#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""GHC linker adapter: prohibit linking the host's C/POSIX libraries."""
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

root = Path('/work/build/runtime')
root.mkdir(parents=True, exist_ok=True)
omitted = {'-lc', '-lm', '-lrt', '-ldl', '-lpthread', '-lffi', '-lCffi', '-lgmp', '-lnuma', '-lzstd'}
def expand(arguments):
    result = []
    for argument in arguments:
        if argument.startswith('@'):
            result.extend(expand(shlex.split(Path(argument[1:]).read_text())))
        else:
            result.append(argument)
    return result

generated = expand(sys.argv[1:])
(root/'ghc-link-arguments.json').write_text(json.dumps(generated, indent=2)+'\n')
arguments = [x for x in generated if x not in omitted and x != '-fuse-ld=gold']
arguments = ['/work/build/runtime/libhouse-rts.a' if x.startswith('-lHSrts-') else x
             for x in arguments]
unexpected = [x for x in arguments if x.startswith('-l') and not x.startswith('-lHS')]
if unexpected:
    raise SystemExit(f'Unreviewed native library dependency: {unexpected}')
command = ['gcc', '-fuse-ld=bfd', '-nostdlib', '-static', '-no-pie',
           '-Wl,--gc-sections', '-Wl,-Map,build/runtime/kernel.map,--cref',
           '-Wl,-T,bootstrap/runtime/link.ld',
           '-Wl,--start-group', *arguments, '-lgcc', '-Wl,--end-group']
(root/'link-command.json').write_text(json.dumps(command, indent=2)+'\n')
result = subprocess.run(command, capture_output=True, text=True)
(root/'link.log').write_text(result.stdout+result.stderr)
missing = sorted(set(re.findall(r"undefined reference to [`']([^'`]+)['`]", result.stderr)))
(root/'undefined-symbols.json').write_text(json.dumps(missing, indent=2)+'\n')
if result.returncode:
    print(f'Freestanding link: {len(missing)} unresolved symbols; see build/runtime/link.log', file=sys.stderr)
    print(result.stderr[-2500:], file=sys.stderr)
raise SystemExit(result.returncode)
