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
import json
from unittest import TestCase
from unittest.mock import Mock, patch

from cibyl.cli.argument import Argument
from cibyl.exceptions.jenkins import JenkinsError
from cibyl.sources.jenkins import (Jenkins, filter_builds, filter_jobs,
                                   safe_request)


class TestSafeRequestJenkinsError(TestCase):
    """Tests for :func:`safe_request`."""

    def test_wraps_errors_jenkins_error(self):
        """Tests that errors coming out of the Jenkins API call
        are wrapped around the JenkinsError type.
        """

        @safe_request
        def request_test():
            raise Exception

        self.assertRaises(JenkinsError, request_test)

    def test_returns_result_when_no_error(self):
        """Tests that the call's output is returned when everything goes right.
        """
        result = {'some_key': 'some_value'}

        @safe_request
        def request_test():
            return result

        self.assertEqual(result, request_test())


class TestJenkinsSource(TestCase):
    """Tests for :class:`Jenkins`."""

    def setUp(self):
        self.jenkins = Jenkins("url", "user", "token")

    # pylint: disable=protected-access
    def test_with_all_args(self):
        """Checks that the object is built correctly when all arguments are
        provided.
        """
        url = 'url/to/jenkins/'
        username = 'user'
        cert = 'path/to/cert.pem'
        token = 'token'

        jenkins = Jenkins(url, username, token, cert)

        self.assertEqual(cert, jenkins.cert)

    def test_with_no_cert(self):
        """Checks that object is built correctly when the certificate is not
        provided.
        """
        url = 'url/to/jenkins/'
        username = 'user'
        cert = None
        token = 'token'

        jenkins = Jenkins(url, username, token, cert)

        self.assertIsNone(jenkins.cert)

    def test_get_jobs_all(self):
        """
            Tests that the internal logic from :meth:`Jenkins.get_jobs` is
            correct.
        """
        self.jenkins.send_request = Mock(return_value={"jobs": []})
        jobs_arg = Mock()
        jobs_arg.value = []

        jobs = self.jenkins.get_jobs(jobs=jobs_arg)
        self.jenkins.send_request.assert_called_with(
                                self.jenkins.jobs_query)
        self.assertEqual(len(jobs), 0)

    def test_get_jobs(self):
        """
            Tests that the internal logic from :meth:`Jenkins.get_jobs` is
            correct.
        """
        response = {"jobs": [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1'},
                    {'_class': 'org..job.WorkflowRun', 'name': "job2",
                     'url': 'url2'},
                    {'_class': 'folder', 'name': 'ansible-empty'}]}
        self.jenkins.send_request = Mock(return_value=response)
        jobs_arg = Mock()
        jobs_arg.value = ["ansible"]

        jobs = self.jenkins.get_jobs(jobs=jobs_arg)
        self.assertEqual(len(jobs), 1)
        self.assertTrue("ansible" in jobs)
        self.assertEqual(jobs["ansible"].name.value, "ansible")
        self.assertEqual(jobs["ansible"].url.value, "url1")

    def test_get_builds(self):
        """
            Tests that the internal logic from :meth:`Jenkins.get_builds` is
            correct.
        """
        response = {'jobs': [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1'}]}
        builds = {'_class': '_empty',
                  'allBuilds': [{'number': 1, 'result': "SUCCESS"},
                                {'number': 2, 'result': "FAILURE"}]}
        self.jenkins.send_request = Mock(side_effect=[response, builds])

        jobs = self.jenkins.get_builds()
        self.assertEqual(len(jobs), 1)
        job = jobs["ansible"]
        self.assertEqual(job.name.value, "ansible")
        self.assertEqual(job.url.value, "url1")
        builds_found = job.builds.value
        self.assertEqual(len(builds_found), 2)
        self.assertEqual(builds_found["1"].build_id.value, "1")
        self.assertEqual(builds_found["1"].status.value, "SUCCESS")
        self.assertEqual(builds_found["2"].build_id.value, "2")
        self.assertEqual(builds_found["2"].status.value, "FAILURE")

    def test_get_last_build(self):
        """
            Tests that the internal logic from :meth:`Jenkins.get_last_build`
        is correct.
        """
        response = {'jobs': [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1',
                              'lastBuild': {'number': 1, 'result': "SUCCESS"}
                              }]}
        self.jenkins.send_request = Mock(side_effect=[response])

        jobs = self.jenkins.get_last_build()
        self.assertEqual(len(jobs), 1)
        job = jobs["ansible"]
        self.assertEqual(job.name.value, "ansible")
        self.assertEqual(job.url.value, "url1")
        self.assertEqual(len(job.builds.value), 1)
        build = job.builds.value["1"]
        self.assertEqual(build.build_id.value, "1")
        self.assertEqual(build.status.value, "SUCCESS")

    def test_get_last_build_from_get_builds(self):
        """
        Test that get_last_build is called when calling get_builds with
        --last-build option.
        """
        response = {'jobs': [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1',
                              'lastBuild': {'number': 1, 'result': "SUCCESS"}
                              }]}
        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = []

        jobs = self.jenkins.get_builds(last_build=arg)
        self.assertEqual(len(jobs), 1)
        job = jobs["ansible"]
        self.assertEqual(job.name.value, "ansible")
        self.assertEqual(job.url.value, "url1")
        self.assertEqual(len(job.builds.value), 1)
        build = job.builds.value["1"]
        self.assertEqual(build.build_id.value, "1")
        self.assertEqual(build.status.value, "SUCCESS")

    def test_get_last_build_job_no_builds(self):
        """Test that get_last_build handles properly a job has no builds."""

        response = {'jobs': [{'_class': 'org.job.WorkflowJob',
                              'name': 'ansible-nfv-branch', 'url': 'url',
                              'lastBuild': None},
                             {'_class': 'folder'}]}

        self.jenkins.send_request = Mock(side_effect=[response])

        jobs = self.jenkins.get_last_build()
        self.assertEqual(len(jobs), 1)
        job = jobs["ansible-nfv-branch"]
        self.assertEqual(job.name.value, "ansible-nfv-branch")
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)

    @patch("requests.get")
    def test_send_request(self, patched_get):
        """
            Test that send_request method parses the response correctly.
        """
        response = {'jobs': [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1'}]}
        patched_get.return_value = Mock(text=json.dumps(response))
        self.assertEqual(response, self.jenkins.send_request("test"))
        patched_get.assert_called_with(
            f'://{self.jenkins.username}:{self.jenkins.token}@/api/jsontest',
            verify=self.jenkins.cert, timeout=None
        )

    @patch("requests.get")
    def test_send_request_with_item(self, patched_get):
        """
            Test that send_request method parses the response correctly.
        """
        response = {'jobs': [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1'}]}
        patched_get.return_value = Mock(text=json.dumps(response))
        self.assertEqual(response, self.jenkins.send_request("test",
                                                             item="item"))
        api_part = "item/api/jsontest"
        patched_get.assert_called_with(
            f'://{self.jenkins.username}:{self.jenkins.token}@/{api_part}',
            verify=self.jenkins.cert, timeout=None
        )

    @patch("requests.get")
    def test_send_request_with_raw_response(self, patched_get):
        """
            Test that send_request returns the raw response.
        """
        response = {'jobs': [{'_class': 'org..job.WorkflowRun',
                              'name': "ansible", 'url': 'url1'}]}
        response = json.dumps(response)
        patched_get.return_value = Mock(text=response)
        self.assertEqual(response,
                         self.jenkins.send_request("test", raw_response=True))

        api_part = "api/jsontest"
        patched_get.assert_called_with(
            f'://{self.jenkins.username}:{self.jenkins.token}@/{api_part}',
            verify=self.jenkins.cert, timeout=None
        )

    def test_get_deployment(self):
        """ Test that get_deployment reads properly the information obtained
        from jenkins.
        """
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        ip_versions = ['4', '6', 'unknown']
        releases = ['17.3', '16', '']
        topologies = ["compute:2,controller:1", "compute:1,controller:2", ""]

        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = []

        jobs = self.jenkins.get_deployment(ip_version=arg)
        self.assertEqual(len(jobs), 3)
        for job_name, ip, release, topology in zip(job_names, ip_versions,
                                                   releases, topologies):
            job = jobs[job_name]
            deployment = job.deployment.value
            self.assertEqual(job.name.value, job_name)
            self.assertEqual(job.url.value, "url")
            self.assertEqual(len(job.builds.value), 0)
            self.assertEqual(deployment.release.value, release)
            self.assertEqual(deployment.ip_version.value, ip)
            self.assertEqual(deployment.topology.value, topology)

    def test_get_deployment_many_jobs(self):
        """ Test that get_deployment reads properly the information obtained
        from jenkins.
        """
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        ip_versions = ['4', '6', 'unknown']
        releases = ['17.3', '16', '']
        topologies = ["compute:2,controller:1", "compute:1,controller:2", ""]

        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})
        for _ in range(12):
            # ensure that there are more than 12 jobs and jenkins source gets
            # deployment information from job name
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': 'test_job', 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = []

        jobs = self.jenkins.get_deployment(ip_version=arg)
        self.assertEqual(len(jobs), 3)
        for job_name, ip, release, topology in zip(job_names, ip_versions,
                                                   releases, topologies):
            job = jobs[job_name]
            deployment = job.deployment.value
            self.assertEqual(job.name.value, job_name)
            self.assertEqual(job.url.value, "url")
            self.assertEqual(len(job.builds.value), 0)
            self.assertEqual(deployment.release.value, release)
            self.assertEqual(deployment.ip_version.value, ip)
            self.assertEqual(deployment.topology.value, topology)

    def test_get_deployment_artifacts_fallback(self):
        """ Test that get_deployment falls back to reading job_names after
        failing to find artifacts.
        """
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        ip_versions = ['4', '6', 'unknown']
        releases = ['17.3', '16', '']
        topologies = ["compute:2,controller:1", "compute:1,controller:2", ""]

        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': {}})
        # each job triggers 2 artifacts requests, if both fail, fallback to
        # search the name
        artifacts_fail = [JenkinsError for _ in range(6)]
        self.jenkins.send_request = Mock(side_effect=[response]+artifacts_fail)
        self.jenkins.add_job_info_from_name = Mock(
                side_effect=self.jenkins.add_job_info_from_name)

        jobs = self.jenkins.get_deployment()
        self.jenkins.add_job_info_from_name.assert_called()
        self.assertEqual(len(jobs), 3)
        for job_name, ip, release, topology in zip(job_names, ip_versions,
                                                   releases, topologies):
            job = jobs[job_name]
            deployment = job.deployment.value
            self.assertEqual(job.name.value, job_name)
            self.assertEqual(job.url.value, "url")
            self.assertEqual(len(job.builds.value), 0)
            self.assertEqual(deployment.release.value, release)
            self.assertEqual(deployment.ip_version.value, ip)
            self.assertEqual(deployment.topology.value, topology)

    def test_get_deployment_artifacts(self):
        """ Test that get_deployment reads properly the information obtained
        from jenkins using artifacts.
        """
        job_names = ['test_17.3_ipv4_job', 'test_16_ipv6_job', 'test_job']
        ip_versions = ['4', '6', 'unknown']
        releases = ['17.3', '16', '']
        topologies = ["compute:2,controller:3", "compute:1,controller:2",
                      "compute:2,controller:2"]

        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': {}})
        artifacts = [
           f"bla\nJP_TOPOLOGY='{topologies[0]}'\nPRODUCT_VERSION=17.3",
           f"bla\nJP_TOPOLOGY='{topologies[1]}'\nPRODUCT_VERSION=16",
           f"bla\nJP_TOPOLOGY='{topologies[2]}'\nPRODUCT_VERSION=",
            ]

        self.jenkins.send_request = Mock(side_effect=[response]+artifacts)

        jobs = self.jenkins.get_deployment()
        self.assertEqual(len(jobs), 3)
        for job_name, ip, release, topology in zip(job_names, ip_versions,
                                                   releases, topologies):
            job = jobs[job_name]
            deployment = job.deployment.value
            self.assertEqual(job.name.value, job_name)
            self.assertEqual(job.url.value, "url")
            self.assertEqual(len(job.builds.value), 0)
            self.assertEqual(deployment.release.value, release)
            self.assertEqual(deployment.ip_version.value, ip)
            self.assertEqual(deployment.topology.value, topology)

    def test_get_deployment_filter_ipv(self):
        """Test that get_deployment filters by ip_version."""
        job_names = ['test_17.3_ipv4_job', 'test_16_ipv6_job', 'test_job']

        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = ["4"]

        jobs = self.jenkins.get_deployment(ip_version=arg)
        self.assertEqual(len(jobs), 1)
        job_name = 'test_17.3_ipv4_job'
        job = jobs[job_name]
        deployment = job.deployment.value
        self.assertEqual(job.name.value, job_name)
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)
        self.assertEqual(deployment.release.value, "17.3")
        self.assertEqual(deployment.ip_version.value, "4")
        self.assertEqual(deployment.topology.value, "")

    def test_get_deployment_filter_topology(self):
        """Test that get_deployment filters by topology."""
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        topology_value = "compute:2,controller:1"
        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = [topology_value]

        jobs = self.jenkins.get_deployment(topology=arg)
        self.assertEqual(len(jobs), 1)
        job_name = 'test_17.3_ipv4_job_2comp_1cont'
        job = jobs[job_name]
        deployment = job.deployment.value
        self.assertEqual(job.name.value, job_name)
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)
        self.assertEqual(deployment.release.value, "17.3")
        self.assertEqual(deployment.ip_version.value, "4")
        self.assertEqual(deployment.topology.value, topology_value)

    def test_get_deployment_filter_release(self):
        """Test that get_deployment filters by release."""
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        response = {'jobs': [{'_class': 'folder'}]}
        topology_value = "compute:2,controller:1"
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = ["17.3"]

        jobs = self.jenkins.get_deployment(release=arg)
        self.assertEqual(len(jobs), 1)
        job_name = 'test_17.3_ipv4_job_2comp_1cont'
        job = jobs[job_name]
        deployment = job.deployment.value
        self.assertEqual(job.name.value, job_name)
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)
        self.assertEqual(deployment.release.value, "17.3")
        self.assertEqual(deployment.ip_version.value, "4")
        self.assertEqual(deployment.topology.value, topology_value)

    def test_get_deployment_filter_topology_ip_version(self):
        """Test that get_deployment filters by topology and ip version."""
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        topology_value = "compute:2,controller:1"
        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = [topology_value]
        arg_ip = Mock()
        arg_ip.value = ["6"]

        jobs = self.jenkins.get_deployment(topology=arg, ip_version=arg_ip)
        self.assertEqual(len(jobs), 0)

    def test_get_deployment_filter_network_backend(self):
        """Test that get_deployment filters by topology and ip version."""
        job_names = ['test_17.3_ipv4_job_2comp_1cont_geneve',
                     'test_16_ipv6_job_1comp_2cont_vxlan', 'test_job']
        topology_value = "compute:2,controller:1"
        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Mock()
        arg.value = ["geneve"]

        jobs = self.jenkins.get_deployment(network_backend=arg)
        self.assertEqual(len(jobs), 1)
        job_name = 'test_17.3_ipv4_job_2comp_1cont_geneve'
        job = jobs[job_name]
        deployment = job.deployment.value
        self.assertEqual(job.name.value, job_name)
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)
        self.assertEqual(deployment.release.value, "17.3")
        self.assertEqual(deployment.ip_version.value, "4")
        self.assertEqual(deployment.topology.value, topology_value)
        self.assertEqual(deployment.network_backend.value, "geneve")

    def test_get_deployment_filter_controller(self):
        """Test that get_deployment filters by controller."""
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        topology_value = "compute:2,controller:1"
        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Argument("compute", arg_type=str, description="", value=["<2"],
                       ranged=True)

        jobs = self.jenkins.get_deployment(controllers=arg)
        self.assertEqual(len(jobs), 1)
        job_name = 'test_17.3_ipv4_job_2comp_1cont'
        job = jobs[job_name]
        deployment = job.deployment.value
        self.assertEqual(job.name.value, job_name)
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)
        self.assertEqual(deployment.release.value, "17.3")
        self.assertEqual(deployment.ip_version.value, "4")
        self.assertEqual(deployment.topology.value, topology_value)

    def test_get_deployment_filter_computes(self):
        """Test that get_deployment filters by computes."""
        job_names = ['test_17.3_ipv4_job_2comp_1cont',
                     'test_16_ipv6_job_1comp_2cont', 'test_job']
        topology_value = "compute:2,controller:1"
        response = {'jobs': [{'_class': 'folder'}]}
        for job_name in job_names:
            response['jobs'].append({'_class': 'org.job.WorkflowJob',
                                     'name': job_name, 'url': 'url',
                                     'lastBuild': None})

        self.jenkins.send_request = Mock(side_effect=[response])
        arg = Argument("compute", arg_type=str, description="", value=["2"],
                       ranged=True)

        jobs = self.jenkins.get_deployment(computes=arg)
        self.assertEqual(len(jobs), 1)
        job_name = 'test_17.3_ipv4_job_2comp_1cont'
        job = jobs[job_name]
        deployment = job.deployment.value
        self.assertEqual(job.name.value, job_name)
        self.assertEqual(job.url.value, "url")
        self.assertEqual(len(job.builds.value), 0)
        self.assertEqual(deployment.release.value, "17.3")
        self.assertEqual(deployment.ip_version.value, "4")
        self.assertEqual(deployment.topology.value, topology_value)


class TestFilters(TestCase):
    """Tests for filter functions in jenkins source module."""
    def test_filter_jobs(self):
        """
            Test that filter_jobs filters the jobs given the user input.
        """
        response = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}]
        args = Mock()
        args.value = ["ans"]
        jobs_filtered = filter_jobs(response, jobs=args)
        expected = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}},
                    ]
        self.assertEqual(jobs_filtered, expected)

    def test_filter_jobs_class(self):
        """
            Test that filter_jobs filters the jobs given the job _class.
        """
        response = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'jenkins.branch.OrganizationFolder',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'com.cloudbees.hudson.plugins.folder.Folder',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'hudson.model.FreeStyleProject',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}]
        jobs_filtered = filter_jobs(response)
        expected = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'hudson.model.FreeStyleProject',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}},
                    ]
        self.assertEqual(jobs_filtered, expected)

    def test_filter_job_name_job_url(self):
        """
            Test that filter_jobs filters the jobs given the user input.
        """
        response = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}]
        job_name = Mock()
        job_name.value = ["ans2"]
        job_url = Mock()
        job_url.value = ["url3"]
        jobs_filtered = filter_jobs(response, job_name=job_name,
                                    job_url=job_url)
        expected = [{'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}]
        self.assertEqual(jobs_filtered, expected)

    def test_filter_job_name(self):
        """
            Test that filter_jobs filters the jobs given the user input.
        """
        response = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}]
        job_name = Mock()
        job_name.value = ["ansible"]
        jobs_filtered = filter_jobs(response, job_name=job_name)
        expected = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}}]
        self.assertEqual(jobs_filtered, expected)

    def test_filter_job_url(self):
        """
            Test that filter_jobs filters the jobs given the user input.
        """
        response = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}
                    ]
        job_url = Mock()
        job_url.value = ["url2"]
        jobs_filtered = filter_jobs(response, job_url=job_url)
        expected = [{'_class': 'org..job.WorkflowRun',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}}]
        self.assertEqual(jobs_filtered, expected)

    def test_filter_job_name_job_url_jobs(self):
        """
            Test that filter_jobs filters the jobs given the user input.
        """
        response = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "test_jobs", 'url': 'url2',
                     'lastBuild': {'number': 2, 'result': "FAILURE"}},
                    {'_class': 'org..job.WorkflowRun',
                     'name': "ans2", 'url': 'url3',
                     'lastBuild': {'number': 0, 'result': "FAILURE"}}]
        args = Mock()
        args.value = ["ans"]
        job_name = Mock()
        job_name.value = ["ansible"]
        job_url = Mock()
        job_url.value = ["url1"]
        jobs_filtered = filter_jobs(response, jobs=args, job_url=job_url,
                                    job_name=job_name)
        expected = [{'_class': 'org..job.WorkflowRun',
                     'name': "ansible", 'url': 'url1',
                     'lastBuild': {'number': 1, 'result': "SUCCESS"}}]
        self.assertEqual(jobs_filtered, expected)

    def test_filter_builds_builds_build_id_build_status_empty(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        builds = Mock()
        builds.value = []
        build_id = Mock()
        build_id.value = ["3"]
        build_status = Mock()
        build_status.value = ["failure"]
        builds_filtered = filter_builds(response, builds=builds,
                                        build_status=build_status,
                                        build_id=build_id)
        expected = []
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_builds_build_id_build_status(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        builds = Mock()
        builds.value = []
        build_id = Mock()
        build_id.value = ["3"]
        build_status = Mock()
        build_status.value = ["success"]
        builds_filtered = filter_builds(response, builds=builds,
                                        build_status=build_status,
                                        build_id=build_id)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'}]
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_builds_build_id(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        builds = Mock()
        builds.value = []
        build_id = Mock()
        build_id.value = ["3"]
        builds_filtered = filter_builds(response, builds=builds,
                                        build_id=build_id)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'FAILURE'}]
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_builds_build_status(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        builds = Mock()
        builds.value = []
        build_status = Mock()
        build_status.value = ["success"]
        builds_filtered = filter_builds(response, builds=builds,
                                        build_status=build_status)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': "5",
                     'result': 'success'}]
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_build_id_build_status(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        build_id = Mock()
        build_id.value = ["3"]
        build_status = Mock()
        build_status.value = ["success"]
        builds_filtered = filter_builds(response,
                                        build_status=build_status,
                                        build_id=build_id)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'}]
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_builds(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        builds = Mock()
        builds.value = ["3", "5"]
        builds_filtered = filter_builds(response, builds=builds)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': "5",
                     'result': 'success'}]
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_build_status(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        build_status = Mock()
        build_status.value = ["success"]
        builds_filtered = filter_builds(response,
                                        build_status=build_status)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': "5",
                     'result': 'success'}]
        self.assertEqual(builds_filtered, expected)

    def test_filter_builds_build_id(self):
        """Test that filter builds filters the builds given the user input."""
        response = [{'_class': 'org..job.WorkflowRun', 'number': 3,
                     'result': 'SUCCESS'},
                    {'_class': 'org..job.WorkflowRun', 'number': 4,
                     'result': 'FAILURE'},
                    {'_class': 'org..job.WorkflowRun', 'number': 5,
                     'result': 'success'}]
        build_id = Mock()
        build_id.value = ["3"]
        builds_filtered = filter_builds(response,
                                        build_id=build_id)
        expected = [{'_class': 'org..job.WorkflowRun', 'number': "3",
                     'result': 'SUCCESS'}]
        self.assertEqual(builds_filtered, expected)
