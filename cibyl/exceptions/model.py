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


class NonSupportedModelType(CibylException):
    """Exception for trying to populate non-supported model"""

    def __init__(self, model_type):
        self.model_type = model_type
        self.message = f"""Not supported type for model: {self.model_type}.
Unable to populate system with pulled data"""
        super().__init__(self.message)


class NoValidSystem(CibylException):
    """Exception for a case when no valid system is found."""

    def __init__(self, valid_systems=None):
        self.message = """No valid system defined."""
        if valid_systems:
            self.message += "\nPlease use one of the following available"
            self.message += " systems:\n"
            for system_name in valid_systems:
                self.message += f"{system_name}\n"
        else:
            self.message += "\nPlease ensure the specified systems are present"
            self.message += " in the configuration."
        super().__init__(self.message)


class InvalidEnvironment(CibylException):
    """Exception for a case when no valid environment is found."""

    def __init__(self, environment, valid_environments=None):
        self.message = f"No such environment: {environment}"
        if valid_environments:
            self.message += "\nPlease use one of the following available"
            self.message += " environments:\n"
            for env_name in valid_environments:
                self.message += f"{env_name}\n"
        else:
            self.message += "\nPlease set at least one environment in the "
            self.message += "configuration file."

        super().__init__(self.message)


class InvalidSystem(CibylException):
    """Exception for a case when non existing system is passed by the user."""

    def __init__(self, system, valid_systems=None):
        self.message = f"No such system: {system}"
        if valid_systems:
            self.message += "\nPlease use one of the following available"
            self.message += " systems:\n"
            for system_name in valid_systems:
                self.message += f"{system_name}\n"
        else:
            self.message += "\nPlease ensure the specified systems are present"
            self.message += " in the configuration."
        super().__init__(self.message)
