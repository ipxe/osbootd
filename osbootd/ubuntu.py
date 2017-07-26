"""An Ubuntu distribution"""

import logging

from cachetools.func import lru_cache
from werkzeug.wrappers import Response
from osbootd.distro import Distro

logger = logging.getLogger(__name__)


class UbuntuLiveDistro(Distro):
    """An Ubuntu live distribution"""

    @classmethod
    def autodetect(cls, tree):
        """Autodetect a distribution tree"""
        return tree.exists('.disk/info') and tree.exists('casper')

    @property
    @lru_cache()
    def info(self):
        """Read the disk information file"""
        return self.tree.read('.disk/info')
    
    @property
    def name(self):
        """Get distribution name"""
        return self.info.split(' ', 1)[0]

    @property
    def version(self):
        """Get distribution version"""
        return self.info.split(' ', 1)[1]

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
