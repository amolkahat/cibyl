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

import logging

from cibyl.exceptions.model import (InvalidEnvironment, InvalidSystem,
                                    NoValidSystem)

LOG = logging.getLogger(__name__)


class Validator:
    """This is a helper class that will filter the configuration according to
    the user input.
    """

    def __init__(self, ci_args: dict):
        self.ci_args = ci_args

    def _check_input_environments(self, all_envs, argument,
                                  exception_to_raise):
        """Check if the user input environments exist in the configuration.

        :param all_envs: Environments defined in the configuration
        :type all_envs: list
        :param argument: Name of the cli argument to check
        :type argument: str
        :raises: InvalidEnvironment
        """

        env_user_input = self.ci_args.get(argument)
        if env_user_input:
            # check if user input environment name exists
            for env_name in env_user_input.value:
                if env_name not in all_envs:
                    raise exception_to_raise(env_name, all_envs)

    def _consistent_environment(self, env):
        """Check if an environment should be used according to user input.

        :param env: Model to validate
        :type env: :class:`.Environment`
        :returns: Whether the environment is consistent with user input
        :rtype: bool
        """
        user_env = self.ci_args.get("env_name")
        if user_env:
            return env.name.value in user_env.value
        return True

    def _consistent_system(self, system):
        """Check if a system should be used according to user input.

        :param system: Model to validate
        :type system: :class:`.System`
        :returns: Whether the system is consistent with user input
        :rtype: bool
        """
        name = system.name.value
        system_type = system.system_type.value
        system_sources = set(source.name for source in system.sources)

        user_system_type = self.ci_args.get("system_type")
        if user_system_type and system_type not in user_system_type.value:
            return False

        user_systems = self.ci_args.get("systems")
        if user_systems and name not in user_systems.value:
            return False

        user_sources = self.ci_args.get("sources")
        if user_sources:
            user_sources_names = set(user_sources.value)
            if not user_sources_names & system_sources:
                return False

        return True

    def validate_environments(self, environments):
        """Filter environments and systems according to user input.

        :returns: Environments and systems that can be used according to user
        input
        :rtype: list, list
        """
        all_envs = []
        all_systems = []
        # first get all environments and systems so we can ensure that the user
        # input is found within the configuration
        for env in environments:
            all_envs.append(env.name.value)
            for system in env.systems:
                all_systems.append(system.name.value)
        self._check_input_environments(all_envs, "env_name",
                                       InvalidEnvironment)
        self._check_input_environments(all_systems, "systems", InvalidSystem)

        # if the user input is good, then filter the environments and systems
        # so we only keep the ones consistent with user input
        user_systems = []
        user_envs = []
        for env in environments:
            env_systems = []
            if not self._consistent_environment(env):
                LOG.debug("Environment %s is not consistent with user input",
                          env.name.value)
                continue
            for system in env.systems:
                if not self._consistent_system(system):
                    LOG.debug("System %s is not consistent with user input",
                              system.name.value)

                    continue
                env_systems.append(system)
            if env_systems:
                # if the environment has no valid systems, we will not pass it
                # back, so for the rest of the execution we will only consider
                # valid environments and systems
                env.systems.value = env_systems
                user_envs.append(env)
                user_systems.extend(env_systems)

        if not user_systems:
            raise NoValidSystem(all_systems)
        return user_envs, user_systems
