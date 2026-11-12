#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the guest's Haskell library graph with the native bignum backend.

This is an incremental freestanding port, not a complete GHC distribution
build. The source and generated configuration headers match the pinned RTS.
Only the resulting linked kernel establishes which platform services it uses.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import toolchain

ROOT = Path('/work')
OUT = ROOT / 'build/runtime/library'


def field(name):
    return subprocess.check_output(
        ['ghc-pkg', 'field', 'ghc-internal', name, '--simple-output'], text=True).strip()


def main():
    source = toolchain.prepare_source() / 'libraries/ghc-internal'
    installed = Path(field('import-dirs'))
    rts = Path(subprocess.check_output(
        ['ghc-pkg', 'field', 'rts', 'include-dirs', '--simple-output'], text=True).strip())
    generated = OUT / 'generated'
    generated.mkdir(parents=True, exist_ok=True)
    includes = [source / 'include', installed / 'include', rts]
    input_files = sorted({Path(__file__).resolve(), ROOT / 'toolchain/lock.json',
                          *[p for p in source.rglob('*') if p.is_file() and
                            (p.suffix in ('.hs', '.hsc', '.h', '.c') or p.name.endswith('.hs-boot'))],
                          *rts.rglob('*.h'), *(installed / 'include').rglob('*.h')})
    input_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_files}
    cache_key = hashlib.sha256(json.dumps(input_hashes, sort_keys=True).encode()).hexdigest()
    archive = OUT / ('lib' + field('hs-libraries') + '.a')
    manifest = OUT / 'build.json'
    if manifest.exists() and archive.exists() and (OUT / 'package.conf.d/package.cache').exists():
        previous = json.loads(manifest.read_text())
        artifacts = previous.get('artifacts_sha256', {})
        if (previous.get('cache_key') == cache_key and artifacts and
                all((OUT / p).exists() and hashlib.sha256((OUT / p).read_bytes()).hexdigest() == digest
                    for p, digest in artifacts.items())):
            print('Guest library cache verified; native bignums.', flush=True)
            return
    # The compiler supplies the real primitive interface (GHC.Iface.Load).
    # Its build still needs a discoverable, empty on-disk interface module.
    prim = generated / 'GHC/Internal/Prim.hs'
    prim.parent.mkdir(parents=True, exist_ok=True)
    prim_text = ('{-# LANGUAGE NoImplicitPrelude #-}\n'
                 'module GHC.Internal.Prim () where\ndefault ()\n')
    if not prim.exists() or prim.read_text() != prim_text:
        prim.write_text(prim_text)
    # Stage narrow platform changes; never edit the verified source tree.
    changes = {}
    for name in ('Fingerprint', 'Exception/Backtrace', 'IO/Encoding', 'Foreign/C/Error'):
        original = source / 'src/GHC/Internal' / (name + '.hs')
        text = original.read_text()
        if name == 'Fingerprint':
            text, count = re.subn(r'^getFileHash path =.*?(?=^data MD5Context)',
                'getFileHash _ = errorWithoutStackTrace "House: file hashing unavailable"\n\n',
                text, flags=re.M | re.S)
            if count != 1:
                raise RuntimeError('Review changed GHC file-hashing implementation')
        elif name == 'Exception/Backtrace':
            replacements = {
                'setBacktraceMechanismState bm enabled = do':
                    'setBacktraceMechanismState IPEBacktrace True =\n    errorWithoutStackTrace "House: IPE backtraces unavailable"\nsetBacktraceMechanismState bm enabled = do',
                'displayIpe  = unlines . mapMaybe (fmap (indent 2) . CloneStack.prettyStackFrameWithIpe) . unsafePerformIO . CloneStack.decodeStackWithIpe':
                    'displayIpe _ = errorWithoutStackTrace "House: IPE backtraces unavailable"',
                '    ipe <- collect IPEBacktrace $ do\n        stack <- CloneStack.cloneMyStack\n        return (Just stack)':
                    '    ipe <- collect IPEBacktrace $\n        errorWithoutStackTrace "House: IPE backtraces unavailable"',
            }
            for old, new in replacements.items():
                if text.count(old) != 1:
                    raise RuntimeError('Review changed GHC backtrace implementation')
                text = text.replace(old, new)
        elif name == 'IO/Encoding':
            replacements = {
                'import qualified GHC.Internal.IO.Encoding.Iconv as Iconv': '',
                "initLocaleEncoding     = unsafePerformIO $ mkTextEncoding' ErrorOnCodingFailure Iconv.localeEncodingName":
                    'initLocaleEncoding     = UTF8.mkUTF8 ErrorOnCodingFailure',
                "initFileSystemEncoding = unsafePerformIO $ mkTextEncoding' RoundtripFailure     Iconv.localeEncodingName":
                    'initFileSystemEncoding = UTF8.mkUTF8 RoundtripFailure',
                "initForeignEncoding    = unsafePerformIO $ mkTextEncoding' IgnoreCodingFailure  Iconv.localeEncodingName":
                    'initForeignEncoding    = UTF8.mkUTF8 IgnoreCodingFailure',
                '_ -> do res <- Iconv.mkIconvEncoding cfm enc\n            case res of\n              Just e -> return e\n              Nothing -> unknownEncodingErr (enc ++ codingFailureModeSuffix cfm)':
                    '_ -> unknownEncodingErr (enc ++ codingFailureModeSuffix cfm)',
            }
            for old, new in replacements.items():
                if text.count(old) != 1:
                    raise RuntimeError('Review changed GHC encoding implementation')
                text = text.replace(old, new)
        else:
            replacements = {
                'import GHC.Internal.Foreign.C.Types':
                    'import GHC.Internal.Foreign.C.Types\nimport GHC.Internal.Foreign.Storable (peek, poke)\nimport GHC.Internal.Show (show)',
                'foreign import ccall unsafe "HsBase.h __hscore_get_errno" get_errno :: IO CInt':
                    'foreign import ccall unsafe "__errno_location" errnoLocation :: IO (Ptr CInt)\nget_errno :: IO CInt\nget_errno = errnoLocation >>= peek',
                'foreign import ccall unsafe "HsBase.h __hscore_set_errno" set_errno :: CInt -> IO ()':
                    'set_errno :: CInt -> IO ()\nset_errno value = errnoLocation >>= \\pointer -> poke pointer value',
            }
            for old, new in replacements.items():
                if text.count(old) != 1:
                    raise RuntimeError('Review changed GHC errno implementation')
                text = text.replace(old, new)
            start = text.index('\n#if defined(javascript_HOST_ARCH)', text.index('errnoToString ::'))
            end = text.index('\n#endif', start) + len('\n#endif')
            text = text[:start] + '\nerrnoToString (Errno code) = return ("House errno " ++ show code)\n' + text[end:]
        target = generated / original.relative_to(source / 'src')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != text:
            target.write_text(text)
        boot = original.with_suffix('.hs-boot')
        if boot.exists():
            target_boot = target.with_suffix('.hs-boot')
            if not target_boot.exists() or target_boot.read_bytes() != boot.read_bytes():
                shutil.copyfile(boot, target_boot)
        changes[str(original.relative_to(source))] = hashlib.sha256(text.encode()).hexdigest()
    for hsc in sorted((source / 'src').rglob('*.hsc')):
        if any(part in ('Windows', 'Windows.hsc', 'POSIX', 'KQueue.hsc', 'ConsoleHandler.hsc') for part in hsc.parts):
            continue
        target = generated / hsc.relative_to(source / 'src').with_suffix('.hs')
        target.parent.mkdir(parents=True, exist_ok=True)
        stamp = target.with_suffix('.sha256')
        if not target.exists() or not stamp.exists() or stamp.read_text() != cache_key:
            subprocess.run(['hsc2hs', *['-I' + str(p) for p in includes],
                            str(hsc), '-o', str(target)], check=True)
            stamp.write_text(cache_key)
    command = ['ghc', '--make', '-no-link', '-fasm', '-O1', '-split-sections',
               '-hide-all-packages', '-package-id', 'rts-1.0.3',
               '-this-unit-id', 'ghc-internal', '-this-package-name', 'ghc-internal',
               '-XHaskell2010', '-XNoImplicitPrelude', '-DBIGNUM_NATIVE',
               '-i', '-i' + str(generated), '-i' + str(source / 'src'),
               *['-I' + str(p) for p in includes], '-outputdir', str(OUT),
               *[str(source / 'src' / ('GHC/Internal/' + name + '.hs')) for name in (
                   'Show', 'Real', 'IO', 'Control/Exception', 'Control/Monad',
                   'Data/List', 'Data/Either', 'Data/Foldable', 'Data/Traversable',
                   'System/IO', 'System/IO/Error', 'Text/Read')]]
    (OUT / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    dependencies = OUT / 'dependencies.mk'
    subprocess.run([command[0], '-M', '-dep-makefile', str(dependencies), *command[2:]], check=True)
    subprocess.run(command, check=True)
    # Read the current dependency graph, rather than archiving stale objects
    # left by a previous graph/configuration in the incremental build folder.
    objects = set()
    for line in dependencies.read_text().splitlines():
        if ':' not in line:
            continue
        for target in line.split(':', 1)[0].split():
            if target.endswith('.o'):
                path = Path(target).resolve()
                if not path.is_relative_to(OUT) or not path.exists():
                    raise RuntimeError(f'Unexpected library object in dependency graph: {path}')
                objects.add(path)
                stub = path.with_name(path.stem + '_stub.o')
                if stub.exists():
                    objects.add(stub)
    objects = sorted(objects)
    if not objects:
        raise RuntimeError('Empty guest library dependency graph')
    c_sources = [source / 'cbits/md5.c']
    c_objects = []
    for c_source in c_sources:
        target = OUT / 'cbits' / c_source.with_suffix('.o').name
        target.parent.mkdir(exist_ok=True)
        subprocess.run(['gcc', '-m32', '-O2', '-ffreestanding', '-fno-pie',
                        '-fno-stack-protector', '-ffunction-sections', '-fdata-sections',
                        *['-I' + str(p) for p in includes], '-I' + str(source / 'cbits'),
                        '-c', str(c_source), '-o', str(target)], check=True)
        c_objects.append(target)
    archive.unlink(missing_ok=True)
    subprocess.run(['ar', 'q', str(archive), *map(str, objects + c_objects)], check=True)
    subprocess.run(['ranlib', str(archive)], check=True)
    # Shadow the installed package only for guest compilations. Its unit id
    # remains wired in, but its interfaces/code come from this source build.
    config = subprocess.check_output(['ghc-pkg', 'describe', 'ghc-internal'], text=True)
    lines = config.splitlines()
    fields = {}
    key = None
    for line in lines:
        if line and not line[0].isspace() and ':' in line:
            key, value = line.split(':', 1)
            fields[key] = value.strip()
        elif key:
            fields[key] += ' ' + line.strip()
    for key in ('import-dirs', 'library-dirs', 'library-dirs-static'):
        fields[key] = str(OUT)
    fields['include-dirs'] = ' '.join(map(str, includes))
    fields['extra-libraries'] = ''
    compiled = {'.'.join(p.relative_to(OUT).with_suffix('').parts) for p in objects
                if p.with_suffix('.hi').exists()}
    for key in ('exposed-modules', 'hidden-modules'):
        fields[key] = ' '.join(n for n in fields[key].split() if n in compiled)
    for key in ('abi', 'dynamic-library-dirs', 'haddock-interfaces', 'haddock-html', 'pkgroot'):
        fields.pop(key, None)
    fields['data-dir'] = str(source)
    db = OUT / 'package.conf.d'
    db.mkdir(exist_ok=True)
    (db / 'ghc-internal.conf').write_text(''.join(f'{k}: {v}\n' for k, v in fields.items()))
    subprocess.run(['ghc-pkg', 'recache', '--package-db', str(db)], check=True)
    artifacts = [archive, *OUT.glob('GHC/**/*.hi'), *db.glob('*'), *generated.rglob('*.hs')]
    (OUT / 'build.json').write_text(json.dumps({
        'cache_key': cache_key, 'input_files_sha256': input_hashes,
        'staged_platform_modules_sha256': changes,
        'artifacts_sha256': {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in artifacts if p.is_file()},
        'bignum_backend': 'native', 'source_archive_sha256': toolchain.LOCK['source']['sha256'],
        'command': command, 'objects': [str(p.relative_to(OUT)) for p in objects],
        'c_sources_sha256': {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in c_sources},
        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    print(f'Guest library built: {len(objects)} Haskell objects; native bignums.', flush=True)


if __name__ == '__main__':
    main()
