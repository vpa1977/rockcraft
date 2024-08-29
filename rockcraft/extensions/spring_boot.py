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

import os
from typing import Tuple
from typing import Any
from typing import Dict
from overrides import override

from .extension import Extension

class SpringBootFramework(Extension):

    def _check_project(self):
        """Ensure that either pom.xml or gradlew is present."""
        if not os.path.exists(f"{self.project_root}/pom.xml") and not os.path.exists(f"{self.project_root}/gradlew"):
            pass

    @property
    def name(self) -> str:
        """Return the normalized name of the rockcraft project."""
        return self.yaml_data["name"].replace("-", "_").lower()

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
        self._check_project()
        return {"run_user": "_daemon_",}


    def gen_install_app_part(self) -> Dict[str, Any]:
        if "spring-boot-framework/install-app" not in self.yaml_data.get("parts", {}):
            if os.path.exists(f"{self.project_root}/pom.xml"):
                return {
                    "plugin": "nil",
                    "source": ".",
                    "source-type": "local",
                    "build-packages": ["default-jdk", "maven"],
                    "override-build": """
                        maven package
                        mkdir -p ${CRAFT_PART_INSTALL}/jar
                        find ${CRAFT_PART_BUILD}/ -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jar \\;
                        craftctl default
                    """
                }
            elif os.path.exists(f"{self.project_root}/gradlew"):
                return {
                    "plugin": "nil",
                    "source": ".",
                    "source-type": "local",
                    "build-packages": ["default-jdk"],
                    "override-build" : """
                        ./gradlew jar --no-daemon
                        mkdir -p ${CRAFT_PART_INSTALL}/jar
                        find ${CRAFT_PART_BUILD}/ -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jar \\;
                        craftctl default
                    """
                }
        return {}

    def get_runtime_app_part(self) -> Dict[str, Any]:
        if "spring-boot-framework/runtime" not in self.yaml_data.get("parts", {}):
            return {
                "plugin": "jlink",
                "after": [ "spring-boot-framework/install-app" ],
                # temporary entries until chisel-releases for openjdk
                # are merged upstream
                "source": "https://github.com/vpa1977/chisel-releases",
                "source-type": "git",
                "source-branch": "24.04-openjdk-21-jre-headless",
            }
        return {}

    def get_parts_snippet(self) -> dict[str, Any]:
        """Return the parts to add to parts."""
        return {
            "spring-boot-framework/install-app" : self.gen_install_app_part(),
            "spring-boot-framework/runtime": self.get_runtime_app_part()
        }