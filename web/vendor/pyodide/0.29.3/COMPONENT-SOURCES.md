# Pyodide 0.29.3 core component and source inventory

This directory contains an unmodified five-file subset extracted from the official
`pyodide-core-0.29.3.tar.bz2` release archive. The accompanying licenses and exact source
locators identify the direct runtime and linked components verified for the `v0.1.0` public
research preview.

This is an owner-reviewed, bounded notice inventory, not an exhaustive software bill of
materials, independent legal opinion, freedom-to-operate conclusion, clinical approval, or
representation about components that are not present in the selected core build.

## Direct runtime

- **Pyodide 0.29.3:** tag `0.29.3`, commit
  `72e3c78d53a32a76e0aca7443ad24e5cae1042d3`, MPL-2.0. The exact license is in
  `LICENSE-PYODIDE.txt`, and corresponding source is available from
  `https://github.com/pyodide/pyodide/tree/0.29.3`.
- **Official core release archive:**
  `https://github.com/pyodide/pyodide/releases/download/0.29.3/pyodide-core-0.29.3.tar.bz2`;
  5,986,900 bytes; SHA-256
  `83b764fe1a0ab6a2d76dba035fbef7284e06dac945a958be2d6447eced592f5a`.
- **CPython 3.13.2:** the tagged build pins
  `https://www.python.org/ftp/python/3.13.2/Python-3.13.2.tgz`; 29,319,380 bytes; SHA-256
  `b8d79530e3b7c96a5cb2d40d431ddb512af4a563e863728d8713039aa50203f9`. The exact CPython
  source license is in `LICENSE-CPYTHON.txt`. Pyodide applies its published CPython patches; this
  repository does not modify the extracted runtime files.

## Linked, generated, and embedded components

- **Emscripten 4.0.9:** the Pyodide tag selects this toolchain. Source:
  `https://github.com/emscripten-core/emscripten/tree/4.0.9`. Its dual MIT/NCSA notice is in
  `LICENSE-EMSCRIPTEN.txt`.
- **musl libc from Emscripten 4.0.9:** source and exact copyright notice:
  `https://github.com/emscripten-core/emscripten/blob/4.0.9/system/lib/libc/musl/COPYRIGHT`;
  copied to `LICENSE-MUSL.txt`.
- **zlib 1.3.1 Emscripten port:** the Emscripten 4.0.9 port pins the `v1.3.1` source archive with
  SHA-512
  `8c9642495bafd6fad4ab9fb67f09b268c69ff9af0f4f20cf15dfc18852ff1f312bd8ca41de761b3f8d8e90e77d79f2ccacd3d4c5b19e475ecf09d021fdfe9088`.
  Source: `https://github.com/madler/zlib/tree/v1.3.1`; notice: `LICENSE-ZLIB.txt`.
- **bzip2 1.0.6 Emscripten port:** the Emscripten 4.0.9 port pins the `1.0.6` archive with
  SHA-512
  `512cbfde5144067f677496452f3335e9368fd5d7564899cb49e77847b9ae7dca598218276637cbf5ec524523be1e8ace4ad36a148ef7f4badf3f6d5a002a4bb2`.
  Source: `https://github.com/emscripten-ports/bzip2/tree/1.0.6`; notice:
  `LICENSE-BZIP2.txt`.
- **libffi:** Pyodide pins commit `f08493d249d2067c8b3207ba46693dd858f95db3`. Source:
  `https://github.com/libffi/libffi/tree/f08493d249d2067c8b3207ba46693dd858f95db3`; notice:
  `LICENSE-LIBFFI.txt`.
- **hiwire:** Pyodide pins commit `6a1e67280a15d929ebeceee54a6358c9c8d5f697`. Source:
  `https://github.com/pyodide/hiwire/tree/6a1e67280a15d929ebeceee54a6358c9c8d5f697`. Its MPL-2.0
  license is byte-identical to `LICENSE-PYODIDE.txt` (SHA-256
  `1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5`).
- **libmpdec, Expat, and HACL\*:** the tagged build statically injects the corresponding CPython
  3.13.2 objects. Notices copied from that source are in `LICENSE-CPYTHON-LIBMPDEC.txt`,
  `LICENSE-CPYTHON-EXPAT.txt`, and `LICENSE-CPYTHON-HACL.txt`.
- **StackFrame:** Pyodide vendors it at `src/js/vendor/stackframe`; its MIT notice is in
  `LICENSE-STACKFRAME.txt`.

Pyodide's `cpython/Setup.local` disables `_sqlite3`, `_ssl`, `_lzma`, `_hashlib`, and `_uuid` for
this core build path. This repository provides the upstream source locations required by the
MPL-2.0 executable-form notice for Pyodide and hiwire; no locally modified third-party runtime
source is distributed.
