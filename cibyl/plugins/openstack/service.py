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

# flake8: noqa from cibyl.cli.argument import Argument
# flake8: noqa from cibyl.models.attribute import AttributeListValue
from cibyl.models.model import Model

# pylint: disable=no-member


class Service(Model):
    """
    Model for services found on Openstack deployment
    """
    # To be implemented in future PR

    API = {}
