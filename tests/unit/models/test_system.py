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

from cibyl.models.attribute import AttributeDictValue
from cibyl.models.ci.build import Build
from cibyl.models.ci.job import Job
from cibyl.models.ci.pipeline import Pipeline
from cibyl.models.ci.system import JobsSystem, PipelineSystem, System
from cibyl.sources.source import Source


class TestSystem(unittest.TestCase):
    """Test the System class."""

    def setUp(self):
        self.name = "test"
        self.system_type = "test_type"
        self.system = System(self.name, self.system_type)
        self.other_system = System(self.name, self.system_type)

    def test_new_system_name(self):
        """Test the name attribute of the System class."""
        system = System("test", "test_type")
        attribute_name = 'name'
        test_name_bool = hasattr(system, attribute_name)
        self.assertTrue(
            test_name_bool,
            msg=f"System lacks an attribute: {attribute_name}")
        self.assertEqual(system.name.value, "test")
        system_name = system.name.value
        self.assertEqual(system_name, "test",
                         msg=f"System should be test, not {system_name}")

    def test_new_system_type(self):
        """Test the type attribute of the System class."""
        system = System("test", "test_type")
        attribute_name = 'system_type'
        test_name_bool = hasattr(system, attribute_name)
        self.assertTrue(
            test_name_bool,
            msg=f"System lacks an attribute: {attribute_name}")
        type_name = system.system_type.value
        msg_str = f"System type should be test_type, not {type_name}"
        self.assertEqual(type_name, "test_type", msg=msg_str)


class TestJobsSystem(unittest.TestCase):
    """Test the JobsSystem class."""

    def setUp(self):
        self.name = "test"
        self.system_type = "test_type"
        self.system = JobsSystem(self.name, self.system_type)
        self.other_system = JobsSystem(self.name, self.system_type)

    def test_add_job(self):
        """Test adding a new job to a system."""
        job = Job("test_job")
        self.system.add_job(job)
        self.assertEqual(len(self.system.jobs.value), 1)
        self.assertEqual(job, self.system.jobs.value["test_job"])

    def test_system_populate(self):
        """Test adding a new job to a system."""
        job = Job("test_job")
        jobs = AttributeDictValue(name='jobs', value={'test_job': job},
                                  attr_type=Job)
        self.system.populate(jobs)
        self.assertEqual(len(self.system.jobs.value), 1)
        self.assertEqual(job, self.system.jobs.value["test_job"])

    @unittest.skip("will be integrated later")
    def test_system_str_jobs(self):
        """Test system str for a system with jobs and builds."""
        build = Build("1", "SUCCESS")
        job = Job("test_job")
        job.add_build(build)
        self.system.add_job(job)
        output = str(self.system)
        expected = """System: test
  Job: test_job
    Build: 1
      Status: SUCCESS"""
        self.assertIn(output, expected)


class TestPipelineSystem(unittest.TestCase):
    """Test the PipelineSystem class."""

    def setUp(self):
        self.name = "test"
        self.system = PipelineSystem(self.name, "zuul")
        self.other_system = PipelineSystem(self.name, "zuul")

    def test_new_system_name(self):
        """Test the type attribute of the PipelineSystem class."""
        self.assertTrue(
            hasattr(self.system, 'name'), msg="System lacks name attribute")
        system_name = self.system.name.value
        error_msg = f"System name should be {self.name}, not {system_name}"
        self.assertEqual(self.system.name.value, self.name,
                         msg=error_msg)

    def test_new_system_type(self):
        """Test the type attribute of the PipelineSystem class."""
        self.assertTrue(
            hasattr(self.system, 'system_type'),
            msg="System lacks type attribute")
        system_type = self.system.system_type.value
        error_msg = f"System type should be zuul, not {system_type}"
        self.assertEqual(self.system.name.value, self.name,
                         msg=error_msg)

    def test_system_comparison(self):
        """Test new PipelineSystem instances comparison."""
        self.assertEqual(
            self.system, self.other_system,
            msg="Systems {self.system.name.value} and \
{self.system.name.value} are not equal")

    def test_system_comparison_other_types(self):
        """Test new PipelineSystem instances comparison."""
        self.assertNotEqual(
            self.system, "test",
            msg=f"System {self.system.name.value} should be different from str"
        )

    def test_system_str(self):
        """Test PipelineSystem __str__ method."""
        self.assertIn("System: ", str(self.system))
        self.assertIn("System: ", str(self.other_system))
        self.assertIn(self.name, str(self.system))
        self.assertIn(self.name, str(self.other_system))

    def test_add_pipeline(self):
        """Test PipelineSystem add pipeline method."""
        pipeline = Pipeline("check")
        self.system.add_pipeline(pipeline)
        self.assertEqual(len(self.system.pipelines.value), 1)
        self.assertEqual(pipeline, self.system.pipelines["check"])

    def test_add_pipeline_with_merge(self):
        """Test PipelineSystem add pipeline method."""
        pipeline = Pipeline("check")
        self.system.add_pipeline(pipeline)
        self.system.add_pipeline(pipeline)
        self.assertEqual(len(self.system.pipelines.value), 1)
        self.assertEqual(pipeline, self.system.pipelines["check"])

    def test_populate(self):
        """Test populating the system."""
        pipeline_name = "check"
        pipeline = Pipeline("check")
        pipelines = AttributeDictValue(name='pipelines',
                                       value={pipeline_name: pipeline},
                                       attr_type=Pipeline)
        self.system.populate(pipelines)
        self.assertEqual(len(self.system.pipelines.value), 1)
        self.assertEqual(pipeline, self.system.pipelines.value[pipeline_name])

    def test_add_source(self):
        """Test adding a new source to a system."""
        source = Source("test_source", driver="jenkins")
        self.system.add_source(source)
        self.assertEqual(len(self.system.sources.value), 1)
        self.assertEqual(source, self.system.sources.value[0])
