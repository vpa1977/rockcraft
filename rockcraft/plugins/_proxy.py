
# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Parse proxy settings from the environment"""
import logging
import os
from urllib.parse import urlparse

from textwrap import dedent

logger = logging.getLogger(__name__)

# Template for the sitecustomize module that we'll add to the payload so that
# the pip-installed packages are found regardless of how the interpreter is
# called.
SITECUSTOMIZE_TEMPLATE = dedent(
    """
    # sitecustomize added by Rockcraft.
    import site
    import sys

    major, minor = sys.version_info.major, sys.version_info.minor
    site_dir = f"/lib/python{major}.{minor}/site-packages"
    dist_dir = "/usr/lib/python3/dist-packages"

    # Add the directory that contains the venv-installed packages.
    site.addsitedir(site_dir)

    if dist_dir in sys.path:
        # Make sure that this site-packages dir comes *before* the base-provided
        # dist-packages dir in sys.path.
        path = sys.path
        site_index = path.index(site_dir)
        dist_index = path.index(dist_dir)

        if dist_index < site_index:
            path[dist_index], path[site_index] = path[site_index], path[dist_index]

    EOF
    """
).strip()

class ProxyProperties:
    protocol: str
    host: str
    port:str
    user: str
    password: str

    def __init__(self, protocol: str, host: str, port: str, user: str, password: str):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.user = user
        self.password = password

class ProxySettings:
    proxies: list[ProxyProperties]
    no_proxy: list[str]


def create_proxy_settings() -> ProxySettings:
    """Create ProxySettings from the environment.

    Returns:
        ProxySettings: structure containing proxy settings.
    """
    settings = ProxySettings()
    settings.no_proxy = [key.strip() for key in os.environ.get("no_proxy", "localhost").split(",")]
    for protocol in ("http", "https"):
        env_name = f"{protocol}_proxy"
        if env_name not in os.environ:
            continue

        proxy_url = urlparse(os.environ[env_name])
        properties = ProxyProperties(protocol, proxy_url.hostname,
                                        str(proxy_url.port),
                                        proxy_url.username,
                                        proxy_url.password)
        settings.proxies.append(properties)
    return settings


def get_gradle_properties(settings: ProxySettings) -> list[str]:
    """Create a property string with proxy settings"""
    ret = []
    for proxy in settings.proxies:
        ret.append(f"-D{proxy.protocol}.proxyHost={proxy.host}")
        ret.append(f"-D{proxy.protocol}.proxyPort={proxy.port}")
        if proxy.user is not None:
            ret.append(f"-D{proxy.protocol}.proxyUser={proxy.user}")
        if proxy.password is not None:
            ret.append(f"-D{proxy.protocol}.proxyPassword={proxy.password}")
        if len(settings.no_proxy) > 0:
            ret.append(f"-D{proxy.protocol}.nonProxyHosts={"|".join(settings.no_proxy)}")
    return ret

def get_gradle_proxy_args():
    return get_gradle_properties(create_proxy_settings())
