"""An operating system distribution"""

from itertools import chain
import logging
import os

from werkzeug.exceptions import NotFound
from werkzeug.routing import Map, Rule, Submount
from werkzeug.wrappers import Request
from werkzeug.wsgi import SharedDataMiddleware
from osbootd.tree import RawTree, IsoTree

logger = logging.getLogger(__name__)

DEFAULT_ROOT = '/var/lib/tftpboot'


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
            Rule('/boot.ipxe', endpoint=self.ep_boot_ipxe),
            Rule('/', endpoint=self.ep_boot_ipxe),
            Rule('/<path:path>', endpoint=self.ep_file,
                 build_only=(not hasattr(self.tree, 'ep_file'))),
            ]
        return rules

    def ep_file(self, request, urls, path=''):
        """Read a file via WSGI"""
        return self.tree.ep_file(request, urls, path=path)

    @staticmethod
    def ep_boot_ipxe(_request, _urls):
        """Generate iPXE boot script"""
        raise NotFound()

    def url(self, urls, path=''):
        """Calculate URL to distribution"""
        return urls.build(self.ep_file, {'path': path}, force_external=True)

    @classmethod
    def autoclass(cls, tree):
        """Autodetect distribution class"""
        def subclasses(parent):
            """Identify all subclasses depth-first"""
            for child in parent.__subclasses__():
                subclasses(child)
                yield child
        for subclass in subclasses(cls):
            if subclass.autodetect(tree):
                return subclass
        return None


class Distros(object):
    """A collection of operating system distributions"""

    @staticmethod
    def walk(root, baseclass=Distro):
        """Autodetect distributions within a filesystem hierarchy"""
        for base, _subdir, files in os.walk(root):
            isos = (IsoTree(os.path.join(base, x))
                    for x in files if x.lower().endswith(".iso"))
            trees = chain([RawTree(base)], isos)
            for tree in trees:
                cls = baseclass.autoclass(tree)
                if cls is not None:
                    yield cls(tree)

    def __init__(self, root=DEFAULT_ROOT, baseclass=Distro):
        logger.info("Searching %s", root)
        rules = []
        for distro in self.walk(root, baseclass):
            path = os.path.splitext(os.path.relpath(distro.tree.root, root))[0]
            logger.info("Found %s %s at %s", distro.name, distro.version, path)
            rules.append(Submount('/%s' % path, distro.rules))
        rules.append(Rule('/<path:path>', endpoint=self.ep_static))
        self.urlmap = Map(rules)
        self.static = SharedDataMiddleware(NotFound(), {'/': root})

    def ep_static(self, _request, _urls, **_kwargs):
        """Get static file"""
        return self.static

    @Request.application
    def __call__(self, request):
        """Dispatch WSGI request"""
        urls = self.urlmap.bind_to_environ(request)
        dispatcher = lambda endpoint, args: endpoint(request, urls, **args)
        return urls.dispatch(dispatcher, catch_http_exceptions=True)
