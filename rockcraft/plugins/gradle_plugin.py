
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

"""The Rockcraft Gradle plugin."""

import logging
from textwrap import dedent
from typing import cast
from typing import Any
from typing import List
from typing import Set
from typing import Dict

from ._proxy import get_gradle_proxy_args
from craft_parts.plugins import maven_plugin
from craft_parts.plugins import properties
from craft_parts.plugins import base
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


class GradlePluginProperties(properties.PluginProperties, base.PluginModel):
    """The part properties used by the gradle plugin."""

    # part properties required by the plugin
    source: str
    gradle_parameters: str = ""
    gradle_use_wrapper: bool = True

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "GradlePluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = base.extract_plugin_properties(
            data, plugin_name="gradle", required=["source"]
        )
        return cls(**plugin_data)

class GradlePlugin(base.JavaPlugin):

    properties_class = GradlePluginProperties

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"gradle"}

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"openjdk-21-jdk-headless"}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""

        options = cast(GradlePluginProperties, self._options)

        gradle = "gradle"
        if options.gradle_use_wrapper:
            gradle = "./gradlew"

        gradle += " ".join(get_gradle_proxy_args())

        if options.gradle_parameters is not None:
            build_cmd = f"{gradle} {options.gradle_parameters}"
        else:
            build_cmd = f"{gradle} jar --no-daemon"

        # move jars into the staging area
        return [
            "export JAVA_HOME=$(dirname $(dirname $(readlink -f /usr/bin/java)))",
            build_cmd,
            "mkdir -p ${CRAFT_PART_INSTALL}/jars",
            r'find ${CRAFT_PART_BUILD}/build/libs -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jars \;',
        ]
