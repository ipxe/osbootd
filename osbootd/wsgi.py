"""WSGI application"""

import logging
import os

from werkzeug.exceptions import NotFound
from werkzeug.routing import Map, Rule, Submount
from werkzeug.wrappers import Request
from werkzeug.wsgi import SharedDataMiddleware
import osbootd.distro

logger = logging.getLogger(__name__)


class Application(object):
    """A WSGI application serving up operating system boot images"""

    def __init__(self, root):
        logger.info("Searching %s", root)
        rules = []
        for distro in osbootd.distro.walk(root):
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
