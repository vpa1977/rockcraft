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

"""An extension for the Java runtime."""

from typing import Tuple
from typing import Any
from typing import Dict
from overrides import override

from .extension import Extension

class JavaRuntime(Extension):

    @staticmethod
    @override
    def get_supported_bases() -> Tuple[str, ...]:
        """Return supported bases."""
        return "bare", "ubuntu@24.04", "ubuntu:24.04"

    @staticmethod
    @override
    def is_experimental(base: str | None) -> bool:
        """Check if the extension is in an experimental state."""
        return True

    @override
    def get_part_snippet(self) -> Dict[str, Any]:
        """Return the part snippet to apply to existing parts."""
        return {}

    def get_root_snippet(self) -> Dict[str, Any]:
        target_jar = (
            self.yaml_data.get("java-runtime/service", {})
            .get("jar", "")
        )

        service_name = (
            self.yaml_data.get("java-runtime/service", {})
            .get("name", "service")
        )

        if len(target_jar) == 0:
            return {}

        return {
            "run_user": "_daemon_",
            "services": {
                service_name: {
                    "override": "replace",
                    "startup": "enabled",
                    "command": f"/opt/java/bin/java -jar {target_jar}",
                    "after": ["statsd-exporter"],
                    "user": "_daemon_",
                },
                "statsd-exporter": {
                    "override": "merge",
                    "command": (
                        "/bin/statsd_exporter --statsd.mapping-config=/statsd-mapping.conf "
                        "--statsd.listen-udp=localhost:9125 "
                        "--statsd.listen-tcp=localhost:9125"
                    ),
                    "summary": "statsd exporter service",
                    "startup": "enabled",
                    "user": "_daemon_",
                },
            },
        }

    def get_parts_snippet(self) -> dict[str, Any]:
        """Return the parts to add to parts."""
        return {
            "java-runtime/java-runtime-image" : {
                "plugin" : "nil",
                "build-packages" : [ "openjdk-21-jdk"],
                "override-build" : "jlink --add-modules ALL-MODULE-PATH --output ${CRAFT_PART_INSTALL}/opt/java"
            },
            "java-runtime/java-runtime-dependencies":  {
                "plugin" : "nil",
                "source" :  "https://github.com/vpa1977/chisel-releases",
                "source-type" : "git",
                "source-branch": "24.04-openjdk-21-slice",
                "override-build": """chisel cut --release ./ --root ${CRAFT_PART_INSTALL} \
                                        base-files_base openjdk-21-jre-headless_core
                                """
            }
        }
