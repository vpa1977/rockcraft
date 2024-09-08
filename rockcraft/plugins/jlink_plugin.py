# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The JLink plugin."""

from typing import Literal, cast

from craft_parts.plugins import Plugin, PluginProperties
from overrides import override


class JLinkPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the JLink plugin."""

    plugin: Literal["jlink"] = "jlink"
    jlink_java_version: int = 21
    jlink_jars: list[str] = []


class JLinkPlugin(Plugin):
    """Create a Java Runtime using JLink."""

    properties_class = JLinkPluginProperties

    @override
    def get_build_packages(self) -> set[str]:
        options = cast(JLinkPluginProperties, self._options)
        return {f"openjdk-{options.jlink_java_version}-jdk"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        return {}

    @override
    def get_build_snaps(self) -> set[str]:
        return set()

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(JLinkPluginProperties, self._options)

        commands = []

        if len(options.jlink_jars) > 0:
            jars = " ".join(["${CRAFT_STAGE}/" + x for x in options.jlink_jars])
            commands.append(f"PROCESS_JARS={jars}")
        else:
            commands.append("PROCESS_JARS=$(find ${CRAFT_STAGE} -type f -name *.jar)")

        # create temp folder
        commands.append("mkdir -p ${CRAFT_PART_BUILD}/tmp")
        # extract jar files into temp folder
        commands.append(
            "(cd ${CRAFT_PART_BUILD}/tmp && for jar in ${PROCESS_JARS}; do jar xvf ${jar}; done;)"
        )
        commands.append("CPATH=$(find ${CRAFT_PART_BUILD}/tmp -type f -name *.jar)")
        commands.append("CPATH=$(echo ${CPATH}:. | sed s'/[[:space:]]/:/'g)")
        commands.append("echo ${CPATH}")
        commands.append(
            """if [ "x${PROCESS_JARS}" != "x" ]; then
                deps=$(jdeps --class-path=${CPATH} -q --recursive  --ignore-missing-deps \
                    --print-module-deps --multi-release """
            + str(options.jlink_java_version)
            + """ ${PROCESS_JARS}); else deps=java.base; fi
            """
        )
        commands.append(
            "INSTALL_ROOT=${CRAFT_PART_INSTALL}/usr/lib/jvm/java-"
            + str(options.jlink_java_version)
            + "-openjdk-${CRAFT_TARGET_ARCH}/"
        )

        commands.append(
            "rm -rf ${INSTALL_ROOT} && jlink --add-modules ${deps} --output ${INSTALL_ROOT}"
        )
        # create /usr/bin/java link
        commands.append(
            "(cd ${CRAFT_PART_INSTALL} && mkdir -p usr/bin && ln -s --relative usr/lib/jvm/java-"
            + str(options.jlink_java_version)
            + "-openjdk-${CRAFT_TARGET_ARCH}/bin/java usr/bin/)"
        )
        commands.append("mkdir -p ${CRAFT_PART_INSTALL}/etc/ssl/certs/java/")
        # link cacerts
        commands.append(
            "cp /etc/ssl/certs/java/cacerts ${CRAFT_PART_INSTALL}/etc/ssl/certs/java/cacerts"
        )
        commands.append("cd ${CRAFT_PART_INSTALL}")
        commands.append(
            "rm -f usr/lib/jvm/java-"
            + str(options.jlink_java_version)
            + "-openjdk-${CRAFT_TARGET_ARCH}/lib/security/cacerts"
        )
        commands.append(
            "ln -s --relative etc/ssl/certs/java/cacerts usr/lib/jvm/java-"
            + str(options.jlink_java_version)
            + "-openjdk-${CRAFT_TARGET_ARCH}/lib/security/cacerts"
        )
        return commands
