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

import json
import logging
import re
from functools import partial
from typing import Dict, List
from urllib.parse import urlparse

import requests
import urllib3

from cibyl.exceptions.jenkins import JenkinsError
from cibyl.models.attribute import AttributeDictValue
from cibyl.models.ci.build import Build
from cibyl.models.ci.job import Job
from cibyl.plugins.openstack.deployment import Deployment
from cibyl.plugins.openstack.utils import translate_topology_string
from cibyl.sources.source import Source, safe_request_generic, speed_index
from cibyl.utils.filtering import (IP_PATTERN, NETWORK_BACKEND_PATTERN,
                                   PROPERTY_PATTERN, RELEASE_PATTERN,
                                   TOPOLOGY_PATTERN, apply_filters,
                                   filter_topology,
                                   satisfy_case_insensitive_match,
                                   satisfy_exact_match, satisfy_regex_match)

LOG = logging.getLogger(__name__)

safe_request = partial(safe_request_generic, custom_error=JenkinsError)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def detect_job_info_regex(job_name, pattern, group_index=0, default=""):
    """Extract information from a jenkins job name using regex, if not present,
    set to a default value.

    :param job: Jenkins Job representation as a dictionary
    :type job: dict
    :returns: The ip version used for the job if present, 'unknown' otherwise
    :rtype: str
    """
    match_job = pattern.search(job_name)
    if match_job:
        return match_job.group(group_index)
    return default


def is_job(job):
    """Check if a given job representation corresponds to a job and not
    a folder or a view.

    :param job: Jenkins Job representation as a dictionary
    :type job: dict
    :returns: Whether the job representation actually corresponds to a job
    :rtype: bool
    """
    job_class = job["_class"].lower()
    return not ("view" in job_class or "folder" in job_class)


def filter_jobs(jobs_found: List[Dict], **kwargs):
    """Filter the result from the Jenkins API according to user input"""
    checks_to_apply = [is_job]

    jobs_arg = kwargs.get('jobs')
    if jobs_arg:
        pattern = re.compile("|".join(jobs_arg.value))
        checks_to_apply.append(partial(satisfy_regex_match, pattern=pattern,
                                       field_to_check="name"))

    job_names = kwargs.get('job_name')
    if job_names:
        checks_to_apply.append(partial(satisfy_exact_match,
                                       user_input=job_names,
                                       field_to_check="name"))

    job_urls = kwargs.get('job_url')
    if job_urls:
        checks_to_apply.append(partial(satisfy_exact_match,
                                       user_input=job_urls,
                                       field_to_check="url"))

    return apply_filters(jobs_found, *checks_to_apply)


def filter_builds(builds_found: List[Dict], **kwargs):
    """Filter the result from the Jenkins API according to user input"""
    checks_to_apply = []

    builds_arg = kwargs.get('builds')
    if builds_arg and builds_arg.value:
        checks_to_apply.append(partial(satisfy_exact_match,
                                       user_input=builds_arg,
                                       field_to_check="number"))

    build_ids = kwargs.get('build_id')
    if build_ids:
        checks_to_apply.append(partial(satisfy_exact_match,
                                       user_input=build_ids,
                                       field_to_check="number"))

    build_status = kwargs.get('build_status')
    if build_status:
        checks_to_apply.append(partial(satisfy_case_insensitive_match,
                                       user_input=build_status,
                                       field_to_check="result"))

    for build in builds_found:
        # ensure that the build number is passed as a string, Jenkins usually
        # sends it as an int
        build["number"] = str(build["number"])

    return apply_filters(builds_found, *checks_to_apply)


# pylint: disable=no-member
class Jenkins(Source):
    """A class representation of Jenkins client."""

    jobs_query = "?tree=jobs[name,url]"
    jobs_builds_query = {0: "?tree=allBuilds[number,result]",
                         1: "?tree=allBuilds[number,result,duration]",
                         2: "?tree=allBuilds[number,result,duration]",
                         3: "?tree=allBuilds[number,result,duration]"}
    jobs_last_build_query = "?tree=jobs[name,url,lastBuild[number,result]]"

    # pylint: disable=too-many-arguments
    def __init__(self, url: str, username: str = None, token: str = None,
                 cert: str = None, name: str = "jenkins",
                 driver: str = "jenkins", enabled: bool = True,
                 priority: int = 0):
        """
            Create a client to talk to a jenkins instance.

            :param url: Jenkins instance address
            :type url: str
            :param username: Jenkins username
            :type username: str
            :param token: Jenkins access token
            :type token: str
            :param url: Jenkins instance address
            :type url: str
            :param cert: Path to a file with SSL certificates
            :type cert: str
        """
        super().__init__(name=name, url=url, driver=driver,
                         enabled=enabled, priority=priority)
        self.username = username
        self.token = token
        self.cert = cert

    @safe_request
    def send_request(self, query, timeout=None, item="",
                     api_entrypoint="/api/json", raw_response=False):
        """
            Send a request to the jenkins instance and parse its json response.

            :param query: Part of the API request that specifies which data to
            request
            :type query: str
            :param timeout: How many seconds to wait for the server to send
            data before giving up
            :type timeout: float
            :param item: item to get information about
            :type item: str
            :param api_entrypoint: API entrypoint to use, by default use
            api/json
            :type api_entrypoint: str
            :param raw_response: Whether to return the text of the response
            without any processing
            :type raw_response: bool
            :returns: Information from the jenkins instance
            :rtype: dict
        """

        def generate_query_url():
            base = urlparse(self.url)

            # Add protocol
            url = f'{base.scheme}://'

            # Add user and pass
            if self.username:
                url += f'{self.username}'

                if self.token:
                    url += f':{self.token}'

                url += '@'

            # Add host name
            url += f'{base.netloc}'

            # Add path
            if item:
                url += f'/{item}'

            url += f'{api_entrypoint}{query}'

            return url

        response = requests.get(
            generate_query_url(), verify=self.cert, timeout=timeout
        )

        response.raise_for_status()
        if raw_response:
            return response.text

        return json.loads(response.text)

    @speed_index({'base': 2})
    def get_jobs(self, **kwargs):
        """
            Get jobs from jenkins server.

            :returns: container of Job objects queried from jenkins server
            :rtype: :class:`AttributeDictValue`
        """
        jobs_found = self.send_request(self.jobs_query)["jobs"]
        jobs_filtered = filter_jobs(jobs_found, **kwargs)

        job_objects = {}
        for job in jobs_filtered:
            name = job.get('name')
            job_objects[name] = Job(name=name, url=job.get('url'))

        return AttributeDictValue("jobs", attr_type=Job, value=job_objects)

    @speed_index({'base': 1, 'last_build': 1})
    def get_builds(self, **kwargs):
        """
            Get builds from jenkins server.

            :returns: container of jobs with build information from
            jenkins server
            :rtype: :class:`AttributeDictValue`
        """

        if kwargs.get('last_build'):
            return self.get_last_build(**kwargs)
        jobs_found = self.get_jobs(**kwargs)
        if kwargs.get('verbosity', 0) > 0 and len(jobs_found) > 80:
            LOG.warning("This might take a couple of minutes...\
try reducing verbosity for quicker query")
        LOG.debug("Requesting builds for %d jobs", len(jobs_found))
        for job_name, job in jobs_found.items():
            builds_info = self.send_request(item=f"job/{job_name}",
                                            query=self.jobs_builds_query.get(
                                                kwargs.get('verbosity'), 0))
            if builds_info:
                LOG.debug("Got %d builds for job %s",
                          len(builds_info["allBuilds"]), job_name)
                builds_to_add = filter_builds(builds_info["allBuilds"],
                                              **kwargs)
                for build in builds_to_add:
                    job.add_build(Build(build["number"], build["result"],
                                        duration=build.get('duration')))

        return jobs_found

    def get_last_build(self, **kwargs):
        """
            Get last build for jobs from jenkins server.

            :returns: container of jobs with build information from
            jenkins server
            :rtype: :class:`AttributeDictValue`
        """

        jobs_found = self.send_request(self.jobs_last_build_query)["jobs"]
        jobs_filtered = filter_jobs(jobs_found, **kwargs)

        job_objects = {}
        for job in jobs_filtered:
            name = job.get('name')

            job_object = Job(name=name, url=job.get('url'))
            if job["lastBuild"]:
                builds_to_add = filter_builds([job["lastBuild"]],
                                              **kwargs)
                for build in builds_to_add:
                    build_obj = Build(build["number"], build["result"],
                                      duration=build.get('duration'))
                    job_object.add_build(build_obj)
            job_objects[name] = job_object

        return AttributeDictValue("jobs", attr_type=Job, value=job_objects)

    @speed_index({'base': 2})
    def get_deployment(self, **kwargs):
        """Get deployment information for jobs from jenkins server.

        :returns: container of jobs with deployment information from
        jenkins server
        :rtype: :class:`AttributeDictValue`
        """
        jobs_found = self.send_request(self.jobs_last_build_query)["jobs"]
        jobs_found = filter_jobs(jobs_found, **kwargs)

        use_artifacts = True
        if len(jobs_found) > 12:
            LOG.warning("Requesting deployment information for %d jobs \
will be based on the job name and approximate, restrict the query for more \
accurate results", len(jobs_found))
            use_artifacts = False

        job_deployment_info = []
        for job in jobs_found:
            job_name = job['name']
            job["ip_version"] = detect_job_info_regex(job_name, IP_PATTERN,
                                                      group_index=1,
                                                      default="unknown")
            network_backend = detect_job_info_regex(job_name,
                                                    NETWORK_BACKEND_PATTERN)
            job["network_backend"] = network_backend
            last_build = job.get("lastBuild")
            if use_artifacts and last_build is not None:
                # if we have a lastBuild, we will have artifacts to pull
                self.add_job_info_from_artifacts(job)
            else:
                self.add_job_info_from_name(job)
            job_deployment_info.append(job)

        checks_to_apply = []
        input_ip_version = kwargs.get('ip_version')
        if input_ip_version and input_ip_version.value:
            checks_to_apply.append(partial(satisfy_exact_match,
                                   user_input=input_ip_version,
                                   field_to_check="ip_version"))

        input_topology = kwargs.get('topology')
        if input_topology and input_topology.value:
            checks_to_apply.append(partial(satisfy_exact_match,
                                   user_input=input_topology,
                                   field_to_check="topology"))

        input_release = kwargs.get('release')
        if input_release and input_release.value:
            checks_to_apply.append(partial(satisfy_exact_match,
                                   user_input=input_release,
                                   field_to_check="release_version"))

        input_network_backend = kwargs.get('network_backend')
        if input_network_backend and input_network_backend.value:
            checks_to_apply.append(partial(satisfy_exact_match,
                                           user_input=input_network_backend,
                                           field_to_check="network_backend"))

        input_controllers = kwargs.get('controllers')
        if input_controllers and input_controllers.value:
            for range_arg in input_controllers.value:
                operator, value = range_arg
                checks_to_apply.append(partial(filter_topology,
                                       operator=operator,
                                       value=value,
                                       component='controller'))

        input_computes = kwargs.get('computes')
        if input_computes and input_computes.value:
            for range_arg in input_computes.value:
                operator, value = range_arg
                checks_to_apply.append(partial(filter_topology,
                                       operator=operator,
                                       value=value,
                                       component='compute'))

        job_deployment_info = apply_filters(job_deployment_info,
                                            *checks_to_apply)

        job_objects = {}
        for job in job_deployment_info:
            name = job.get('name')
            job_objects[name] = Job(name=name, url=job.get('url'))
            # TODO: (jgilaber) query for infra_type, nodes and services
            deployment = Deployment(job["release_version"], "unknown",
                                    [], [], ip_version=job["ip_version"],
                                    topology=job["topology"],
                                    network_backend=job["network_backend"])
            job_objects[name].add_deployment(deployment)

        return AttributeDictValue("jobs", attr_type=Job, value=job_objects)

    def add_job_info_from_artifacts(self, job: Dict[str, str]):
        """Add information to the job by querying the last build artifacts.

        :param job: Dictionary representation of a jenkins job
        :type job: dict
        """
        possible_artifacts = [".envrc", "artifacts/jp.env"]
        job_name = job['name']
        artifact = None
        for artifact_path in possible_artifacts:
            artifact_url = f"job/{job_name}/lastBuild/artifact/{artifact_path}"
            try:
                artifact = self.send_request(item=artifact_url, query="",
                                             api_entrypoint="",
                                             raw_response=True)
                break
            except JenkinsError:
                LOG.debug("Found no artifact %s for job %s", artifact_path,
                          job_name)
                continue
        if artifact is None:
            self.add_job_info_from_name(job)
            return
        for line in artifact.split("\n"):
            if "TOPOLOGY=" in line:
                topology_str = detect_job_info_regex(line, PROPERTY_PATTERN,
                                                     group_index=1)
                topology_str = topology_str.replace('"', '')
                topology_str = topology_str.replace("'", '')
                job["topology"] = topology_str
            elif "PRODUCT_VERSION" in line:
                job["release_version"] = detect_job_info_regex(line,
                                                               RELEASE_PATTERN)
        if "topology" not in job or "release_version" not in job:
            self.add_job_info_from_name(job)

    def add_job_info_from_name(self, job:  Dict[str, str]):
        """Add information to the job by using regex on the job name.

        :param job: Dictionary representation of a jenkins job
        :type job: dict
        """
        job_name = job['name']
        short_topology = detect_job_info_regex(job_name,
                                               TOPOLOGY_PATTERN)
        if short_topology:
            # due to the regex used, short_topology may contain a trailing
            # underscore that should be removed
            short_topology = short_topology.rstrip("_")
            job["topology"] = translate_topology_string(short_topology)
        else:
            job["topology"] = ""
        job["release_version"] = detect_job_info_regex(job_name,
                                                       RELEASE_PATTERN)
