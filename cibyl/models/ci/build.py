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
# pylint: disable=no-member
from typing import Dict

from cibyl.cli.argument import Argument
from cibyl.models.attribute import AttributeDictValue
from cibyl.models.ci.test import Test
from cibyl.models.model import Model
from cibyl.utils.colors import Colors


class Build(Model):
    """General model for a job build """
    API = {
        'build_id': {
            'attr_type': str,
            'arguments': [Argument(name='--build-id', arg_type=str,
                                   nargs='*', func='get_builds',
                                   description="Build ID")]
        },
        'status': {
            'attr_type': str,
            'arguments': [Argument(name='--build-status', arg_type=str,
                                   func='get_builds',
                                   description="Build status")]
        },
        'duration': {
            'attr_type': int,
            'arguments': [],
        },
        'tests': {
            'attr_type': Test,
            'attribute_value_class': AttributeDictValue,
            'arguments': [Argument(name='--tests', arg_type=str,
                                   nargs='*', func='get_tests',
                                   description="Job test")]
        }
    }

    def __init__(self, build_id: str, status: str = None,
                 duration: int = None, tests: Dict[str, Test] = None):
        if status is not None:
            status = status.upper()
        super().__init__({'build_id': build_id, 'status': status,
                          'duration': duration, 'tests': tests})

    def __str__(self, indent=0, verbosity=0):
        indent_space = indent*' '
        build_str = Colors.blue(
            f"{indent_space}Build: ") + f"{self.build_id.value}"
        if self.status.value:
            build_str += Colors.blue(f"\n{indent_space}  Status: ")
            if self.status.value == "SUCCESS":
                build_str += Colors.green(f"{self.status.value}")
            if self.status.value == "FAILURE":
                build_str += Colors.red(f"{self.status.value}")
            if self.status.value == "UNSTABLE":
                build_str += Colors.yellow(f"{self.status.value}")
        if verbosity > 0 and self.duration.value:
            duration_in_min = self.duration.value / 60000
            build_str += Colors.blue(f"\n{indent_space}  Duration: ") + \
                f"{duration_in_min:.2f}m"
        if self.tests.value:
            for test in self.tests.values():
                build_str += f"\n{test.__str__(indent+2, verbosity)}"
        return build_str

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.build_id.value == other.build_id.value

    def add_test(self, test: Test):
        """Add a test to the build.

        :param test: Test to add to the build
        :type test: Test
        """
        test_name = test.name.value
        if test_name in self.tests:
            self.tests[test_name].merge(test)
        else:
            self.tests[test_name] = test

    def merge(self, other):
        """Merge the information of two build objects representing the same
        build.

        :param other: The Build object to merge
        :type other: :class:`.Build`
        """
        if not self.status.value:
            self.status.value = other.status.value
        for test in other.tests.values():
            self.add_test(test)
