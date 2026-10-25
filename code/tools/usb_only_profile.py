"""Explicit, fully hashed service source snapshot shared by kernel and CPL3."""
from pathlib import Path
import hashlib
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = 'usb-only-services'
MODULE = 'lib/hardware_profile.dg'
DEFAULT_BYTES = ("// Default desktop/storage policy. Explicit USB builds override this module.\n"
                 "module lib.hardware_profile;\n"
                 "pub const USB_ONLY:bool=false;\n"
                 "pub const FAT_AUDIT_BYTES:usize=32768;\n").encode()
USB_BYTES = ("// Generated USB-only input, shared by kernel and every service.\n"
             "module lib.hardware_profile;\n"
             "pub const USB_ONLY:bool=true;\n"
             "pub const FAT_AUDIT_BYTES:usize=2097152;\n").encode()


def _graph(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('USB service input directory missing or linked')
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('USB service input contains links')
        if path.is_file() and path.suffix == '.dg':
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not 1 <= len(result) <= 2048 or MODULE not in result:
        raise ValueError('USB service input graph incomplete')
    return result


def _expected(original):
    staged = dict(original)
    staged[MODULE] = hashlib.sha256(USB_BYTES).hexdigest()
    return dict(version=1, usb_only=True, source=DIRECTORY + '/' + MODULE,
                sha256=staged[MODULE], fat_audit_bytes=2097152,
                services_sources=original, staged_sources=staged)


def generate(output, *, source_root=ROOT):
    source = Path(source_root).resolve() / 'services'
    original = _graph(source)
    if (source / MODULE).read_bytes() != DEFAULT_BYTES:
        raise ValueError('default hardware profile differs from its contract')
    staged = Path(output).resolve() / DIRECTORY
    if staged.exists():
        raise FileExistsError('USB snapshot already exists; choose a new output')
    for name in original:
        target = staged / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    (staged / MODULE).write_bytes(USB_BYTES)
    if _graph(source) != original:
        raise ValueError('services changed during USB snapshot creation')
    metadata = _expected(original)
    verify(output, metadata, source_root=source_root)
    return staged, metadata


def verify(output, metadata, *, source_root=ROOT):
    """Read-only exact source and staged-graph validation; never regenerate."""
    source = Path(source_root).resolve() / 'services'
    original = _graph(source)
    if (source / MODULE).read_bytes() != DEFAULT_BYTES:
        raise ValueError('default hardware profile contract changed')
    if (not isinstance(metadata, dict) or metadata != _expected(original)
            or type(metadata.get('version')) is not int
            or metadata.get('usb_only') is not True
            or type(metadata.get('fat_audit_bytes')) is not int):
        raise ValueError('USB profile metadata/source graph differs')
    output = Path(output).resolve()
    staged = output / DIRECTORY
    if not staged.resolve().is_relative_to(output) or _graph(staged) != metadata['staged_sources']:
        raise ValueError('USB staged service graph differs')
    if (staged / MODULE).read_bytes() != USB_BYTES:
        raise ValueError('USB policy module differs')
