# pylint: disable=no-member
"""
#    Copyright 2022 Red Hat
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
from typing import Dict

from cibyl.cli.argument import Argument
from cibyl.models.attribute import AttributeDictValue
from cibyl.models.ci.build import Build
from cibyl.models.model import Model


class Job(Model):
    """
        General model for a CI job. Holds basic information such as its
        name, builds and url.

    """
    API = {
        'name': {
            'attr_type': str,
            'arguments': [Argument(name='--job-name', arg_type=str,
                                   description="Job name",
                                   func='get_jobs')]
        },
        'url': {
            'attr_type': str,
            'arguments': [Argument(name='--job-url', arg_type=str,
                                   func='get_jobs',
                                   description="Job URL")]
        },
        'builds': {
            'attr_type': Build,
            'attribute_value_class': AttributeDictValue,
            'arguments': [Argument(name='--builds', arg_type=str,
                                   nargs="*", func="get_builds",
                                   description="Job builds"),
                          Argument(name='--last-build', arg_type=str,
                                   func='get_builds', nargs=0,
                                   description="Last build for job")]
        }
    }

    def __init__(self, name: str, url: str = None,
                 builds: Dict[str, Build] = None):
        super().__init__({'name': name, 'url': url,
                          'builds': builds})

    def __str__(self, indent=0, verbosity=0):
        indent_space = indent*' '
        job_str = f"{indent_space}Job: {self.name.value}"
        if verbosity > 0 and self.url.value:
            job_str += f"\n{indent_space}  URL: {self.url.value}"
        if self.builds.value:
            for build in self.builds.values():
                job_str += f"\n{build.__str__(indent+2, verbosity)}"
        return job_str

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name.value == other.name.value

    def add_build(self, build: Build):
        """Add a build to the job.

        :param build: Build to add to the job
        :type build: Build
        """
        build_id = build.build_id.value
        if build_id in self.builds:
            self.builds[build_id].merge(build)
        else:
            self.builds[build_id] = build

    def merge(self, other):
        """Merge the information of two job objects representing the same
        job.

        :param other: The Job object to merge
        :type other: :class:`.Job`
        """
        if not self.url.value:
            self.url.value = other.url.value
        for build in other.builds.values():
            self.add_build(build)
