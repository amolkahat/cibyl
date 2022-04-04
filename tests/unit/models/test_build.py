"""
# Copyright 2022 Red Hat
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
import unittest

from cibyl.models.ci.build import Build
from cibyl.models.ci.test import Test


class TestBuild(unittest.TestCase):
    """Test Build CI model."""

    def setUp(self):
        self.build_id = 'test-build'
        self.build_status = 'FAILURE'
        self.build = Build(build_id=self.build_id)
        self.second_build = Build(build_id=self.build_id)

    def test_build_id(self):
        """Test new Build id attribute"""
        self.assertTrue(
            hasattr(self.build, 'build_id'),
            msg="Build lacks build_id attribute")

        self.assertEqual(
            self.build.build_id.value, self.build_id,
            msg=f"Build id is {self.build.build_id.value}. \
Should be {self.build_id}")

    def test_build_status(self):
        """Test new Build status attribute."""
        self.assertTrue(
            hasattr(self.build, 'status'), msg="Build lacks status attribute")

        self.assertEqual(
            self.build.status.value, None,
            msg=f"Build default status is {self.build.status.value}. \
Should be None")

        self.assertEqual(
            self.second_build.status.value, None,
            msg=f"Build default status is {self.second_build.status.value}.\
 Should be None")

        self.build.status.value = self.build_status

        self.assertEqual(
            self.build.status.value, self.build_status,
            msg="New build status is {self.build.status.value}. \
Should be {self.build_status}")

    def test_builds_comparison(self):
        """Test new Build instances comparison."""
        self.assertEqual(
            self.build, self.second_build,
            msg=f"Builds {self.build.build_id.value} and \
{self.second_build.build_id.value} are not equal")

    def test_builds_comparison_other_types(self):
        """Test new Build instances comparison."""
        self.assertNotEqual(
            self.build, "test",
            msg=f"Build {self.build.build_id.value} should be different from \
str")

    def test_build_str(self):
        """Test Build __str__ method."""
        self.assertIn('Build: ', str(self.build))
        self.assertIn(self.build_id, str(self.build))
        self.assertIn('Build: ', str(self.second_build))

        self.second_build.status.value = self.build_status

        self.assertIn('Build: ', str(self.second_build))
        self.assertIn('Status: ', str(self.second_build))
        self.assertIn(self.build_id, str(self.second_build))

    def test_build_merge(self):
        """Test Build merge method."""
        test = Test("test_name", "failure")
        self.build.status.value = "SUCCESS"
        self.build.add_test(test)
        self.second_build.merge(self.build)
        self.assertEqual(self.second_build.status.value, "SUCCESS")
        self.assertEqual(len(self.second_build.tests), 1)
        test_obj = self.second_build.tests["test_name"]
        self.assertEqual(test_obj.name.value, "test_name")
        self.assertEqual(test_obj.result.value, "FAILURE")

    def test_build_str_complete(self):
        """Test Build __str__ method."""
        test = Test("test_name", "failure")
        self.build.add_test(test)
        self.build.status.value = "SUCCESS"
        self.build.duration.value = 60000
        build_str = self.build.__str__(verbosity=2)
        self.assertIn('Build: ', build_str)
        self.assertIn(self.build_id, build_str)
        self.assertIn('Duration:', build_str)
        self.assertIn('1.00m', build_str)
        self.assertIn('Test:', build_str)

    def test_build_str_all_status(self):
        """Test Build str for various status strings."""
        statuses = ["SUCCESS", "FAILURE", "UNSTABLE"]
        for status in statuses:
            self.build.status.value = status
            test_str = str(self.build)
            self.assertIn('Status: ', test_str)
            self.assertIn(status, test_str)

    def test_build_add_existing_test(self):
        """Test Build add_test method with existing Test."""
        test = Test("test_name")
        test2 = Test("test_name", "failure")
        self.build.add_test(test)
        self.build.add_test(test2)
        test_obj = self.build.tests["test_name"]
        self.assertEqual(test_obj.name.value, "test_name")
        self.assertEqual(test_obj.result.value, "FAILURE")
