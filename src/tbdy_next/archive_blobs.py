"""Lossless archive storage shared by replay, receipt verification, reports and the gateway."""
import gzip
from functools import lru_cache
from hashlib import file_digest, sha256
from io import BytesIO
import os
from pathlib import Path
import re
import stat
import zlib
from tempfile import NamedTemporaryFile

# Uploaded requests have separate HTTP limits. These limits apply to expanded local artifacts.
MAX_SOURCE_BYTES = 512 * 1024 * 1024
PACK_THRESHOLD = 4 * 1024 * 1024
_CHUNK = 1024 * 1024
_MAGIC = b"TBDY-ARCHIVE-BLOB-v1 "
_REFERENCE = re.compile(rb"TBDY-ARCHIVE-BLOB-v1 ([0-9a-f]{64}) ([1-9][0-9]{0,9})\n\Z")
_PATH = re.compile(r"RUN-[0-9a-f]{32}\Z")


def _direct(path):
    return not (path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _blob_root(path):
    if not _PATH.fullmatch(path.parent.name) or not _direct(path.parent) or not _direct(path.parent.parent):
        raise ValueError("ARCHIVE_REFERENCE_OUTSIDE_RECEIPT_ROOT")
    directory = path.parent.parent / ".archive-blobs"
    if directory.exists() and not _direct(directory):
        raise ValueError("ARCHIVE_BLOB_DIRECTORY_UNSAFE")
    return directory


def _transfer(stream, target, size):
    h = sha256()
    count = 0
    while chunk := stream.read(min(_CHUNK, size + 1 - count)):
        count += len(chunk)
        if count > size:
            raise ValueError("ARCHIVE_EXPANDED_SIZE_MISMATCH")
        h.update(chunk)
        if target is not None:
            target.write(chunk)
    if count != size:
        raise ValueError("ARCHIVE_EXPANDED_SIZE_MISMATCH")
    return h.hexdigest()


def _read_blob(blob, target, size, digest):
    if not _direct(blob) or not blob.is_file():
        raise ValueError("ARCHIVE_BLOB_UNSAFE")
    try:
        with gzip.open(blob, "rb") as stream:
            actual = _transfer(stream, target, size)
    except (OSError, EOFError, zlib.error) as exc:
        raise ValueError("ARCHIVE_BLOB_INVALID_OR_INCOMPLETE") from exc
    if actual != digest:
        raise ValueError("ARCHIVE_BLOB_HASH_MISMATCH")
    return actual


def copy_archive(path, target=None, *, limit=MAX_SOURCE_BYTES):
    """Stream and hash a raw legacy file or a bounded, content-addressed reference."""
    path = Path(path)
    if not path.is_file() or not _direct(path) or not 0 < path.stat().st_size <= limit:
        raise ValueError("ARCHIVE_INPUT_MISSING_OR_UNSAFE")
    with path.open("rb") as stream:
        if stream.read(len(_MAGIC)) != _MAGIC:
            stream.seek(0)
            size = os.fstat(stream.fileno()).st_size
            if not 0 < size <= limit:
                raise ValueError("ARCHIVE_EXPANDED_SIZE_LIMIT")
            return _transfer(stream, target, size)
        stream.seek(0)
        ref = _REFERENCE.fullmatch(stream.read(160))
        if not ref:
            raise ValueError("INVALID_ARCHIVE_REFERENCE")
        digest, size = ref[1].decode("ascii"), int(ref[2])
        if size > limit:
            raise ValueError("ARCHIVE_EXPANDED_SIZE_LIMIT")
        blob = _blob_root(path) / (digest + ".gz")
        return _read_blob(blob, target, size, digest)


if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import msvcrt

    class _BasicInfo(ctypes.Structure):
        _fields_ = [(name, ctypes.c_longlong) for name in ("created", "accessed", "written", "changed")] + [
            ("attributes", wintypes.DWORD)]

    _get_basic = ctypes.WinDLL("kernel32", use_last_error=True).GetFileInformationByHandleEx
    _get_basic.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    _get_basic.restype = wintypes.BOOL


def _identity(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ValueError("ARCHIVE_INPUT_MISSING_OR_UNSAFE")
    changed = info.st_ctime_ns
    if os.name == "nt":
        # Python 3.12 st_ctime on Windows is creation time. NTFS ChangeTime also
        # detects an in-place edit followed by restoration of the old last-write time.
        with path.open("rb") as stream:
            basic = _BasicInfo()
            known = _get_basic(msvcrt.get_osfhandle(stream.fileno()),0,ctypes.byref(basic),ctypes.sizeof(basic))
            changed = basic.changed if known else None
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, changed


@lru_cache(maxsize=4096)
def _stored_digest(path, identity):
    with path.open("rb") as stream:
        prefix = stream.read(160)
        stream.seek(0)
        digest = file_digest(stream, "sha256").hexdigest()
    if _identity(path) != identity:
        raise ValueError("ARCHIVE_CHANGED_DURING_VERIFICATION")
    return digest, prefix


def _content_key(path, identity):
    # A filesystem without reliable change times must read the bytes on each check.
    return (_stored_digest if identity[-1] is not None else _stored_digest.__wrapped__)(path,identity)


def archive_storage_identity(path):
    """Identify the direct file and, for an archive pointer, its compressed backing file."""
    path = Path(path)
    identity = _identity(path)
    parts = [identity]
    if identity[2] <= 160:
        with path.open("rb") as stream:
            prefix = stream.read(160)
        if _identity(path) != identity:
            raise ValueError("ARCHIVE_CHANGED_DURING_VERIFICATION")
        if prefix.startswith(_MAGIC):
            ref = _REFERENCE.fullmatch(prefix)
            if not ref:
                raise ValueError("INVALID_ARCHIVE_REFERENCE")
            blob = _blob_root(path) / (ref[1].decode("ascii") + ".gz")
            parts.append(_identity(blob))
    return parts if all(item[1] and item[-1] is not None for item in parts) else None


def archive_file_hash(path):
    """Cache verified bytes by file identity. Track a referenced gzip independently of its pointer."""
    path = Path(path)
    identity = _identity(path)
    stored, prefix = _content_key(path, identity)
    if not prefix.startswith(_MAGIC):
        return stored
    ref = _REFERENCE.fullmatch(prefix)
    if not ref or identity[2] != len(prefix):
        raise ValueError("INVALID_ARCHIVE_REFERENCE")
    blob = _blob_root(path) / (ref[1].decode("ascii") + ".gz")
    compressed, _ = _content_key(blob, _identity(blob))
    return stored + ":" + compressed


def archive_bytes(path, *, limit=MAX_SOURCE_BYTES):
    with BytesIO() as output:
        copy_archive(path, output, limit=limit)
        return output.getvalue()


def store_archive(path, raw, *, digest=None):
    """Publish only complete bytes. Independent runs share immutable, verified compressed blobs."""
    path = Path(path)
    if not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("ARCHIVE_EXPANDED_SIZE_LIMIT")
    actual_sha = sha256(raw).hexdigest()
    if digest is not None and actual_sha != digest:
        raise ValueError("ARCHIVE_INPUT_HASH_MISMATCH")
    if len(raw) < PACK_THRESHOLD:
        with path.open("xb") as stream:
            stream.write(raw)
        return
    digest = actual_sha
    directory = _blob_root(path)
    directory.mkdir(exist_ok=True)
    blob = directory / (digest + ".gz")
    if not blob.exists():
        with NamedTemporaryFile(dir=directory, delete=False) as temp:
            pending = Path(temp.name)
        try:
            with pending.open("wb") as target, gzip.GzipFile(filename="", mode="wb", fileobj=target,
                                                           compresslevel=1, mtime=0) as stream:
                stream.write(raw)
            try:
                # On Windows rename is atomic and fails if a concurrent writer published first.
                if os.name == "nt":
                    os.rename(pending, blob)
                else:
                    os.link(pending, blob)
            except FileExistsError:
                pass
        finally:
            pending.unlink(missing_ok=True)
    _read_blob(blob, None, len(raw), digest)
    with path.open("xb") as stream:
        stream.write(_MAGIC + digest.encode("ascii") + b" " + str(len(raw)).encode("ascii") + b"\n")
