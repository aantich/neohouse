#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Boot House's character terminal in a host terminal or a QEMU window."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import toolchain

ROOT = Path(__file__).resolve().parents[1]


def command(*, window=False, fullscreen=None):
    if fullscreen is None:
        fullscreen = window and sys.platform == 'darwin'
    qemu = shutil.which('qemu-system-i386')
    if not qemu:
        raise SystemExit('qemu-system-i386 is required')
    result = [qemu, '-name', 'House - native Haskell OS',
              '-machine', 'pc-i440fx-11.1', '-accel', 'tcg,thread=single',
              '-cpu', 'qemu32', '-smp', '1', '-m', '256',
              '-monitor', 'none', '-parallel', 'none', '-nic', 'none',
              '-serial', 'chardev:console',
              '-kernel', str(ROOT / 'build/runtime/kernel.elf'),
              '-append', 'house.shell=1', '-no-reboot',
              '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
    if window or fullscreen:
        display = ('cocoa,zoom-to-fit=on,zoom-interpolation=off' if sys.platform == 'darwin'
                   else 'gtk,zoom-to-fit=on')
        # With no VGA device, this serial terminal is the first and only QEMU
        # display. Its VT100 renderer needs no new guest video/keyboard driver.
        result += ['-vga', 'none', '-display', display,
                   '-chardev', 'vc,id=console,cols=100,rows=30']
        if fullscreen:
            result += ['-full-screen']
    else:
        result += ['-display', 'none', '-chardev', 'stdio,id=console,signal=off']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-build', action='store_true')
    display = parser.add_mutually_exclusive_group()
    display.add_argument('--window', action='store_true', help='Show the guest in QEMU (scaled fullscreen on macOS)')
    display.add_argument('--fullscreen', action='store_true', help='Open a scaled fullscreen QEMU window')
    display.add_argument('--windowed', action='store_true', help='Open a smaller resizable QEMU window')
    args = parser.parse_args()
    window = args.window or args.fullscreen or args.windowed
    if not window and not sys.stdin.isatty():
        raise SystemExit('Run this script in a normal interactive terminal')
    if not args.no_build:
        toolchain.run(['sh', 'scripts/build-runtime.sh'])
    if window:
        print('Booting House in its own QEMU window. Type help, then halt to exit.', flush=True)
    try:
        fullscreen = True if args.fullscreen else False if args.windowed else None
        result = subprocess.run(command(window=window, fullscreen=fullscreen))
    except KeyboardInterrupt:
        raise SystemExit(0)
    raise SystemExit(0 if result.returncode == 33 else result.returncode)


if __name__ == '__main__':
    main()
