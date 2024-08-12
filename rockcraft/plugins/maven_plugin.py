
# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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

"""The Rockcraft Maven plugin."""

import logging
from textwrap import dedent
from typing import cast
from typing import List
from typing import Set

from craft_parts.plugins import maven_plugin
from overrides import override  # type: ignore[reportUnknownVariableType]

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


class MavenPlugin(maven_plugin.MavenPlugin):
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"maven", "openjdk-21-jdk"}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(maven_plugin.MavenPluginProperties, self._options)

        mvn_cmd = ["mvn", "package"]
        if self._use_proxy():
            settings_path = self._part_info.part_build_dir / ".parts/.m2/settings.xml"
            maven_plugin.MavenPlugin._create_settings(settings_path)
            mvn_cmd += ["-s", str(settings_path)]
        # maven places jar files under target/
        return [
            " ".join(mvn_cmd + options.maven_parameters),
            "mkdir -p ${CRAFT_PART_INSTALL}/jars",
            r'find ${CRAFT_PART_BUILD}/target -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jars \;',
        ]
