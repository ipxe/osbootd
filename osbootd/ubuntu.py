"""An Ubuntu distribution"""

import logging
import re
from collections import defaultdict
from cStringIO import StringIO

from cachetools.func import lru_cache
from werkzeug.wrappers import Response
from osbootd.distro import Distro

logger = logging.getLogger(__name__)


class UbuntuDistro(Distro):
    """An Ubuntu distribution"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return tree.exists('README.diskdefines')

    @property
    @lru_cache()
    def diskdefines(self):
        """Read the disk definition file"""
        defs = defaultdict(str)
        for line in StringIO(self.tree.read('README.diskdefines')):
            m = re.match(r'^\s*#define\s+(?P<key>\w+)\s+(?P<val>.+?)\s*$', line)
            if m:
                defs[m.group('key')] = m.group('val')
        return defs

    @property
    def name(self):
        """Get distribution name"""
        return self.diskdefines['DISKNAME'].split(' ', 1)[0]

    @property
    def version(self):
        """Get distribution version"""
        return self.diskdefines['DISKNAME'].split(' ', 1)[-1]


class UbuntuNetbootDistro(UbuntuDistro):
    """An Ubuntu netboot distribution"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return (super(UbuntuNetbootDistro, cls).autodetect(tree) and
                tree.exists('install/netboot'))

    def ep_boot_ipxe(self, _request, _urls):
        """Generate iPXE boot script"""
        script = ''.join(x + '\n' for x in (
            "#!ipxe",
            "kernel install/netboot/ubuntu-installer/%(arch)s/linux"
            " initrd=initrd.gz",
            "initrd install/netboot/ubuntu-installer/%(arch)s/initrd.gz",
            "boot",
            )) % {
                'arch': self.diskdefines['ARCH'],
            }
        return Response(script, content_type='text/plain')


class UbuntuLiveDistro(UbuntuDistro):
    """An Ubuntu live distribution"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return (super(UbuntuLiveDistro, cls).autodetect(tree) and
                tree.exists('casper'))

    def ep_boot_ipxe(self, _request, _urls):
        """Generate iPXE boot script"""
        script = ''.join(x + '\n' for x in (
            "#!ipxe",
            "kernel casper/vmlinuz.efi initrd=initrd.lz"
            " boot=casper live-media=/lib/casper live-media-path=/",
            "initrd casper/initrd.lz",
            "initrd casper/filesystem.squashfs /lib/casper/filesystem.squashfs",
            "boot",
            ))
        return Response(script, content_type='text/plain')
