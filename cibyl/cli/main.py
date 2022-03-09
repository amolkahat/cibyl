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
import sys

from cibyl.orchestrator import Orchestrator
from cibyl.utils.logger import configure_logging

# CLASSMAP is used to map the plugins classes
# with plugin name so it should be easy to
# import while running.

CLASSMAP = {"openstack": "Deployment"}

def get_config_file_path(arguments):
    """Returns config file path if one was passed with --config argument

    :param arguments: A list of strings representing the arguments and their
                      values, defaults to None
    :type arguments: str, optional
    """
    config_file_path = None
    for i, item in enumerate(arguments[1:]):
        if item == "--config":
            config_file_path = arguments[i + 2]
    return config_file_path


def get_config_log(arguments):
    """Returns configuration related to logging

    :param arguments: A list of strings representing the arguments and their
                      values, defaults to None
    :type arguments: str, optional
    :returns: Dictionary with the logging-related configuration
    :rtype: dict[str, str]
    """
    log_config = {"log_file": "cibyl_output.log", "log_mode": "both",
                  "debug": False}
    for i, item in enumerate(arguments[1:]):
        if item == "--log-file":
            log_config["log_file"] = arguments[i + 2]
        elif item == "--log-mode":
            log_config["log_mode"] = arguments[i+2]
        elif item == "--debug":
            log_config["debug"] = True
    return log_config


def load_plugins(arguments):
    """
    :param arguments: A list of string respresenting the arguments and their
                      values, defaults to None
    """
    plugin_name = []
    for arg, value in enumerate(arguments[1:]):
        if value == "--plugin":
            plugin_name.append(arguments[arg + 2])
        elif value == "-p":
            plugin_name.append(arguments[arg + 2])
    loaded_plugins = []
    for plugin in plugin_name:
        try:
            loaded_plugins.append(
                __import__(f"cibyl.plugins.{plugin}"))
        except (ImportError, ModuleNotFoundError) as error:
            raise ImportError(f"Failed to import: {plugin}") from error
    return loaded_plugins


def main():
    """CLI main entry."""

    # We parse it from sys.argv instead of argparse parser because we want
    # to run the app parser only once, after we update it with the loaded
    # arguments from the CI models based on the loaded configuration file

    #plugins = load_plugins(sys.argv)
    load_plugins(sys.argv)
    config_file_path = get_config_file_path(sys.argv)
    log_config = get_config_log(sys.argv)
    configure_logging(log_config)

    orchestrator = Orchestrator(config_file_path)
    orchestrator.load_configuration()
    orchestrator.create_ci_environments()
    # Add arguments from CI & product models to the parser of the app
    for env in orchestrator.environments:
        orchestrator.extend_parser(attributes=env.API)
    # We can parse user's arguments only after we have loaded the
    # configuration and extended based on it the parser with arguments
    # from the CI models
    orchestrator.parser.parse()
    orchestrator.run_query()
    orchestrator.publisher.publish(orchestrator.environments)


if __name__ == "__main__":
    main()
