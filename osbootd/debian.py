"""A Debian distribution"""

import logging
import re
from collections import defaultdict

from cachetools.func import lru_cache
from werkzeug.wrappers import Response
from osbootd.distro import Distro

logger = logging.getLogger(__name__)


class DebianDistro(Distro):
    """A Debian distribution"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return tree.exists('.disk/info')

    @property
    @lru_cache()
    def diskinfo(self):
        """Read the disk information file"""
        m = re.match(r'^(?P<name>.+)\s(?P<version>\d[\d\.]*)',
                     self.tree.read('.disk/info'))
        return m.groupdict() if m else defaultdict(str)

    @property
    def name(self):
        """Get distribution name"""
        return self.diskinfo['name']

    @property
    def version(self):
        """Get distribution version"""
        return self.diskinfo['version']


class DebianLiveDistro(DebianDistro):
    """A Debian live distribution"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return (super(DebianLiveDistro, cls).autodetect(tree) and
                tree.exists('live'))

    def ep_boot_ipxe(self, _request, urls):
        """Generate iPXE boot script"""
        kernel = next(self.tree.iglob('live/vmlinuz-*'), 'live/vmlinuz')
        initrd = next(self.tree.iglob('live/initrd.img-*'), 'live/initrd.img')
        script = ''.join(x + '\n' for x in (
            "#!ipxe",
            "kernel %(kernel)s initrd=initrd.img boot=live fetch=%(squashfs)s",
            "initrd -n initrd.img %(initrd)s",
            "boot",
            )) % {
                'kernel': kernel,
                'initrd': initrd,
                'squashfs': self.url(urls, 'live/filesystem.squashfs'),
            }
        return Response(script, content_type='text/plain')
