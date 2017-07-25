"""An operating system distribution"""

from itertools import chain
import logging
import os

from werkzeug.exceptions import NotFound
from werkzeug.routing import Rule
from osbootd.tree import RawTree, IsoTree

logger = logging.getLogger(__name__)


class Distro(object):
    """An operating system distribution"""

    def __init__(self, tree):
        self.tree = tree

    @classmethod
    def autodetect(cls, _tree):
        """Autodetect a distribution tree"""
        return False

    @property
    def name(self):
        """Get distribution name (e.g. "Fedora")"""
        return None

    @property
    def version(self):
        """Get distribution version (e.g. "26")"""
        return None

    @property
    def rules(self):
        """Construct routing rules"""
        rules = [
            Rule('/boot.ipxe', endpoint=self.ep_boot_script),
            Rule('/<path:path>', endpoint=self.ep_file,
                 build_only=(not hasattr(self.tree, 'ep_file'))),
            ]
        return rules

    def ep_file(self, request, urls, path=''):
        """Read a file via WSGI"""
        return self.tree.ep_file(request, urls, path=path)

    @staticmethod
    def ep_boot_script(_request, _urls):
        """Generate boot script"""
        raise NotFound()


def autodetect(tree):
    """Autodetect distribution class"""
    def subclasses(cls):
        """Identify all subclasses depth-first"""
        for subclass in cls.__subclasses__():
            subclasses(subclass)
            yield subclass
    for cls in subclasses(Distro):
        if cls.autodetect(tree):
            return cls
    return None


def walk(root):
    """Autodetect distributions within a filesystem hierarchy"""
    for base, _subdir, files in os.walk(root):
        isos = (IsoTree(os.path.join(base, x))
                for x in files if x.lower().endswith(".iso"))
        trees = chain([RawTree(base)], isos)
        for tree in trees:
            cls = autodetect(tree)
            if cls is not None:
                yield cls(tree)
