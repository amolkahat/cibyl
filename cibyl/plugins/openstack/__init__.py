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
from cibyl.cli.argument import Argument
from cibyl.plugins.openstack.deployment import Deployment


def add_deployment(self, deployment: Deployment):
    """Add a deployment to the job.

    :param deployment: Deployment to add to the job
    :type deployment: :class:`.Deployment`
    """
    self.deployment.value = deployment


class Plugin:
    """Extend a CI model with Openstack specific models and methods."""
    plugin_attributes_to_add = {
        'deployment': {'add_method': 'add_deployment'}
        }

    def _extend(self, model_name):
        for _, attr_value in model_name.items():
            if 'attr_type' in attr_value.keys() and \
               attr_value['attr_type'].__name__ == "Job":
                attr_value['attr_type'].API['deployment'] = {
                    'attr_type': Deployment,
                    'arguments': [Argument(
                        name="--deployment",
                        arg_type=str,
                        nargs="*",
                        description="Openstack deployment")]}
                attr_value['attr_type'].plugin_attributes.update(
                        self.plugin_attributes_to_add)
                setattr(attr_value['attr_type'], 'add_deployment',
                        add_deployment)

            if hasattr(attr_value['attr_type'], 'API'):
                self._extend(attr_value['attr_type'].API)
