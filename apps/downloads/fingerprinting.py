"""
Insertion and recovery of the fingerprint inside the distributed content.

PLACEHOLDER technique: the identifier is appended as a marker at the end of the
file bytes. It travels inside the content (not in the file name) and can be
recovered with `extract`, but it is trivially removable. Replace `embed` and
`extract` with the final technique per file type; the rest of the system only
depends on these two functions.
"""

MARKER_PREFIX = b'\n%%FINGERPRINT:'
MARKER_SUFFIX = b'%%\n'


def embed(data, fingerprint):
    """Return a copy of `data` carrying the fingerprint."""
    return data + MARKER_PREFIX + fingerprint.encode('ascii') + MARKER_SUFFIX


def extract(data):
    """Return the fingerprint carried by `data`, or None if there is none."""
    start = data.rfind(MARKER_PREFIX)
    if start == -1:
        return None
    start += len(MARKER_PREFIX)
    end = data.find(MARKER_SUFFIX, start)
    if end == -1:
        return None
    try:
        return data[start:end].decode('ascii')
    except UnicodeDecodeError:
        return None
