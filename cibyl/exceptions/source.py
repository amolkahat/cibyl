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
from cibyl.exceptions import CibylException


class NoSupportedSourcesFound(CibylException):
    """Exception for a case where non of the sources of a single system is
       implementing the function of the argument the user is interested in
    """

    def __init__(self, system, function):
        self.message = f"""Couldn't find any enabled source for the system
{system} that implements the function {function}.
"""
        super().__init__(self.message)


class NoValidSources(CibylException):
    """Exception for a case when no valid source is found."""

    def __init__(self, system):
        self.system = system
        self.message = f"""No valid source defined for the system
{self.system}.  Please ensure the specified sources with --source argument
are present in the configuration.
"""
        super().__init__(self.message)
