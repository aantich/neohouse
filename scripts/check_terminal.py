#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Drive the guest terminal over its real emulated UART and verify responses."""
import argparse
import hashlib
import json
from pathlib import Path
import selectors
import subprocess
import time
import terminal
import toolchain

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-build', action='store_true')
    args = parser.parse_args()
    if not args.no_build:
        toolchain.run(['sh', 'scripts/build-runtime.sh'])
    output = ROOT / 'build/terminal'
    output.mkdir(parents=True, exist_ok=True)
    command = terminal.command()
    # signal=off is valid for both a pipe and an interactive terminal.
    log = bytearray()
    checked = []
    code = None
    failure = None
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    def until(marker, start):
        deadline = time.monotonic() + 20
        while marker not in log[start:]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f'Timed out waiting for {marker!r}')
            for key, _ in selector.select(min(remaining, 1)):
                data = key.fileobj.read(4096)
                if not data:
                    raise RuntimeError(f'QEMU exited while waiting for {marker!r}')
                log.extend(data)
        return bytes(log[start:])

    def send(text, expected):
        start = len(log)
        # Send after the prompt so UART receive buffers cannot overflow during
        # boot. QEMU's chardev then applies UART receive-buffer backpressure.
        process.stdin.write(text)
        response = until(b'house> ', start)
        if expected not in response:
            raise RuntimeError(f'{text!r}: missing {expected!r} in {response!r}')
        checked.append(text.decode('ascii', errors='backslashreplace'))

    try:
        until(b'house> ', 0)
        send(b'help\r', b'help  mem  gc  selftest  echo TEXT  clear  halt\r\n')
        send(b'mem\r', b'Heap capacity: ')
        send(b'gc\r', b'Major GC completed\r\n')
        send(b'echo hlelo\x08\x08\x08\x08ello\r', b'\r\nhello\r\n')
        send(b'bad command\x15echo reset\r', b'\r\nreset\r\n')
        send(b'echo crlf\r\n', b'\r\ncrlf\r\n')
        send(b'echo lf\n', b'\r\nlf\r\n')
        send(b'echo codX\x7fe\r', b'\r\ncode\r\n')
        send(b'echo ar\x1b[Drow\r', b'\r\narrow\r\n')
        send(b'echo stale\x03', b'^C\r\n')
        send(b'clear\r', b'\x1b[2J\x1b[H')
        send(b'echo ' + b'x' * 300 + b'\r', b'\r\n' + b'x' * 251 + b'\r\n')
        send(b'unknown\r', b'Unknown command; type help\r\n')
        send(b'selftest\r', b'Standalone Haskell GC checkpoint passed; collections=24;')
        start = len(log)
        process.stdin.write(b'halt\r')
        until(b'Haskell entry completed\r\n', start)
        code = process.wait(timeout=5)
        if code != 33:
            raise RuntimeError(f'Unexpected QEMU exit status {code}')
    except Exception as error:
        failure = str(error)
    finally:
        if process.poll() is None:
            process.kill()
        code = process.wait()
        selector.close()
        log.extend(process.stdout.read() or b'')
        process.stdin.close()
        process.stdout.close()
    (output / 'serial.log').write_bytes(log)
    (output / 'run.json').write_text(json.dumps({
        'checkpoint': 'haskell-serial-terminal', 'command': command,
        'kernel_sha256': hashlib.sha256((ROOT / 'build/runtime/kernel.elf').read_bytes()).hexdigest(),
        'commands_checked': checked, 'qemu_exit_code': code,
        'passed': failure is None, 'failure': failure,
    }, indent=2) + '\n')
    print(log.decode('ascii', errors='replace'), end='')
    if failure:
        raise SystemExit(failure)
    print('Haskell serial terminal checkpoint passed.')


if __name__ == '__main__':
    main()
