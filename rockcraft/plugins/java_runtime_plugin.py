
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

class JavaRuntimePluginProperties(properties.PluginProperties, base.PluginModel):
    """The part properties used by the gradle plugin."""

    java_runtime_jars: list[str] = []

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "JavaRuntimePluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = base.extract_plugin_properties(
            data, plugin_name="java-runtime")
        return cls(**plugin_data)

class JavaRuntimePlugin(base.Plugin):

    properties_class = JavaRuntimePluginProperties

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return {}

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"openjdk-21-jdk-headless", "ca-certificates-java"}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""

        options = cast(JavaRuntimePluginProperties, self._options)

        commands = []

        # install Java dependencies
        commands.append("chisel cut --release ./ --root ${CRAFT_PART_INSTALL} base-files_base openjdk-21-jre-headless_security")

        # enumerate jar files
        # assume that build plugin deployed them to the staging directory/jars
        if len(options.java_runtime_jars):
            jars = " ".join(["${CRAFT_STAGE}/" + x  for x in  options.java_runtime_jars])
            commands.append(f"PROCESS_JARS={jars}")
        else:
            commands.append("PROCESS_JARS=$(find ${CRAFT_STAGE}/jars -type f -name *.jar)")

        # create temp folder
        commands.append("mkdir -p ${CRAFT_PART_BUILD}/tmp")
        # extract jar files into temp folder
        commands.append("(cd ${CRAFT_PART_BUILD}/tmp && for jar in ${PROCESS_JARS}; do jar xvf ${jar}; done;)")
        commands.append("cpath=$(find ${CRAFT_PART_BUILD}/tmp -type f -name *.jar)")
        commands.append("cpath=$(echo ${cpath} | sed s'/[[:space:]]/:/'g)")
        commands.append("echo ${cpath}");
        commands.append("deps=$(jdeps --class-path=${cpath} -q --recursive  --ignore-missing-deps --print-module-deps --multi-release 21 ${PROCESS_JARS})")
        commands.append("install_root=${CRAFT_PART_INSTALL}/usr/lib/jvm/java-21-openjdk-${CRAFT_TARGET_ARCH}/")

        commands.append("rm -rf ${install_root} && jlink --add-modules ${deps} --output ${install_root}")
        # create /usr/bin/java link
        commands.append("(cd ${CRAFT_PART_INSTALL} && mkdir -p usr/bin && ln -s --relative usr/lib/jvm/java-21-openjdk-${CRAFT_TARGET_ARCH}/bin/java usr/bin/)")
        commands.append("mkdir -p ${CRAFT_PART_INSTALL}/etc/ssl/certs/java/")
        # link cacerts
        commands.append("cp /etc/ssl/certs/java/cacerts ${CRAFT_PART_INSTALL}/etc/ssl/certs/java/cacerts")
        commands.append("cd ${CRAFT_PART_INSTALL}")
        commands.append("rm -f usr/lib/jvm/java-21-openjdk-${CRAFT_TARGET_ARCH}/lib/security/cacerts")
        commands.append("ln -s --relative etc/ssl/certs/java/cacerts usr/lib/jvm/java-21-openjdk-${CRAFT_TARGET_ARCH}/lib/security/cacerts")

        return commands
