"""WSGI application"""

import functools
import logging

from werkzeug.wrappers import Request
import osbootd.distro

logger = logging.getLogger(__name__)


class Application(object):
    """A WSGI application serving up operating system boot images"""

    @staticmethod
    @functools.lru_cache()
    def distros(**kwargs):
        """Launch application

        Launch an application configured using the osbootd.*
        environment variables.
        """
        return osbootd.distro.Distros(**kwargs)

    @Request.application
    def __call__(self, request):
        kwargs = {k.split('.', 1)[1]: v
                  for k, v in request.environ.items()
                  if k.startswith('osbootd.')}
        return self.distros(**kwargs)
