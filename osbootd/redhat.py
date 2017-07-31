"""A Red Hat distribution (including derivatives)"""

import configparser
import functools
import logging

from werkzeug.wrappers import Response
from osbootd.distro import Distro

logger = logging.getLogger(__name__)


class RedHatDistro(Distro):
    """A Red Hat distribution (including derivatives)"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return tree.exists('.treeinfo')

    @functools.lru_cache()
    def readinfo(self, filename):
        """Read a .INI format configuration file"""
        info = configparser.ConfigParser()
        info.read_string(self.tree.read(filename).decode())
        return info

    @property
    def treeinfo(self):
        """Read product metadata treeinfo file"""
        return self.readinfo('.treeinfo')

    @property
    def name(self):
        """Get distribution name"""
        if self.treeinfo.has_section('release'):
            return self.treeinfo.get('release', 'name')
        else:
            return self.treeinfo.get('general', 'family')

    @property
    def version(self):
        """Get distribution version"""
        if self.treeinfo.has_section('release'):
            return self.treeinfo.get('release', 'version')
        else:
            return self.treeinfo.get('general', 'version')

    def ep_boot_ipxe(self, _request, urls):
        """Generate iPXE boot script"""
        script = ''.join(x + '\n' for x in (
            "#!ipxe",
            "kernel images/pxeboot/vmlinuz initrd=initrd.img repo=%(repo)s",
            "initrd images/pxeboot/initrd.img",
            "boot",
            )) % {
                'repo': self.url(urls),
            }
        return Response(script, content_type='text/plain')
