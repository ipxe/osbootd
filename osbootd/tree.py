"""A directory tree

Provide an abstraction of a directory tree (either a raw filesystem or
an ISO image).
"""

import logging
import mimetypes
import os
import threading
import zlib
from datetime import datetime
from time import time

import iso9660
import pyiso9660
import pycdio
from werkzeug.exceptions import NotFound, Forbidden
from werkzeug.http import is_resource_modified, http_date
from werkzeug.wrappers import BaseResponse
from werkzeug.wsgi import wrap_file

logger = logging.getLogger(__name__)

CACHE_MAX_AGE = (60 * 60 * 12)


class DirectoryTree(object):
    """An abstract directory tree"""

    def __init__(self, root):
        self.root = root


class RawTree(DirectoryTree):
    """A directory tree within a raw filesystem"""

    def exists(self, path):
        """Check existence of a file"""
        return os.path.exists(os.path.join(self.root, path))

    def read(self, path):
        """Read a (small) file"""
        with open(os.path.join(self.root, path), 'rb') as f:
            data = f.read()
        return data


class IsoTree(DirectoryTree):
    """An directory tree within an ISO image"""

    def __init__(self, root):
        super(IsoTree, self).__init__(root)
        self.iso = iso9660.ISO9660.IFS(source=self.root,
                                       iso_mask=pyiso9660.EXTENSION_ALL)
        self.fh = open(self.root, 'rb')
        self.lock = threading.Lock()
        st_mtime = os.fstat(self.fh.fileno()).st_mtime
        self.mtime = datetime.fromtimestamp(st_mtime)
        self.etag = ('%s-%08x' % (st_mtime, zlib.adler32(self.root)))

    def __del__(self):
        self.fh.close()
        self.iso.close()

    def isostat(self, path):
        """Find file within ISO image"""
        with self.lock:
            try:
                stat = self.iso.stat(path)
            except TypeError:
                stat = None # Work around a bug in iso9660.py
        return stat

    def exists(self, path):
        """Check existence of a file"""
        return self.isostat(path) is not None

    def read(self, path):
        """Read a (small) file"""
        stat = self.isostat(path)
        if stat is None:
            raise IOError("No such ISO file or directory: '%s'" % path)
        with self.lock:
            _psize, data = self.iso.seek_read(stat['LSN'], stat['sec_size'])
        return data[:stat['size']]

    def ep_file(self, request, _urls, path=''):
        """Read a file via WSGI"""

        # Check for unmodified requests
        etag = ('%s-%08x' % (self.etag, zlib.adler32(path)))
        headers = [
            ('Date', http_date()),
            ('Etag', ('"%s"' % etag)),
            ('Cache-Control', ('max-age=%d, public' % CACHE_MAX_AGE)),
            ]
        if not is_resource_modified(request.environ, etag,
                                    last_modified=self.mtime):
            return BaseResponse(status=304, headers=headers)

        # Check for nonexistent files and for directories
        stat = self.isostat(path.encode())
        if stat is None:
            raise NotFound()
        if stat['is_dir']:
            raise Forbidden()

        # Construct file-like object
        start = (stat['LSN'] * pycdio.ISO_BLOCKSIZE)
        size = stat['size']
        filelike = IsoFile(self.fh, start, size, self.lock)
        wrapped = wrap_file(request.environ, filelike)

        # Construct WSGI response
        mimetype = (mimetypes.guess_type(path)[0] or 'text/plain')
        headers.extend((
            ('Content-Length', str(size)),
            ('Content-Type', mimetype),
            ('Last-Modified', http_date(self.mtime)),
            ('Expires', http_date(time() + CACHE_MAX_AGE)),
            ))
        return BaseResponse(wrapped, headers=headers, direct_passthrough=True)


class IsoFile(object):
    """A WSGI wrappable file within an ISO image

    This class implements the methods required to function as a
    file-like object for the WSGI file wrapper.

    The file descriptor is duplicated to allow for the possibility of
    the WSGI gateway calling the underlying operating system close()
    function.  Duplicated file descriptors share a current file
    offset; we therefore maintain our own concept of file offset and
    use a per-tree lock to guard against race conditions with
    concurrent threads.
    """

    def __init__(self, fh, start, size, lock):
        self.fh = os.fdopen(os.dup(fh.fileno()), 'rb')
        self.start = start
        self.size = size
        self.lock = lock
        self.offset = 0

    def __del__(self):
        self.fh.close()

    def close(self):
        """Close file"""
        self.fh.close()

    def fileno(self):
        """Get underlying file descriptor

        This may be used by the WSGI gateway to send the underlying
        file portion via sendfile().
        """
        return self.fh.fileno()

    def tell(self):
        """Get starting offset

        This may be used by the WSGI gateway to send the underlying
        file portion via sendfile().
        """
        return self.start

    def read(self, size=None):
        """Read file contents

        This may be used by the WSGI gateway to send the underlying
        file if sendfile() is not available.  It may also be used by
        the WSGI application if the WSGI gateway provides no
        file_wrapper method.
        """
        logger.warning('sendfile() is not enabled')
        with self.lock:
            self.fh.seek(self.start + self.offset)
            remaining = (self.size - self.offset)
            if size is None or size > remaining:
                size = remaining
            data = self.fh.read(size)
            self.offset += len(data)
        return data
