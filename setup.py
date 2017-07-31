#!/usr/bin/env python3

from distutils.core import setup

wsgidir = '/usr/libexec/osbootd'
httpconfdir = '/etc/httpd/conf.d'

setup(
    name="osbootd",
    version="0.1",
    description="Operating System Boot Image Daemon",
    author="Michael Brown",
    author_email="mbrown@fensystems.co.uk",
    packages=['osbootd'],
    data_files=[
        (wsgidir, ['osbootd-wsgi']),
        (httpconfdir, ['osbootd.conf']),
        ],
    )
