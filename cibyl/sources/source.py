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
from typing import Dict

import requests

from cibyl.cli.argument import Argument
from cibyl.exceptions.source import NoSupportedSourcesFound
from cibyl.utils.attrdict import AttrDict

LOG = logging.getLogger(__name__)


def safe_request_generic(request, custom_error):
    """Decorator that wraps any errors coming out of a call around a
    custom_error class.

    :param request: The unsafe call to watch errors on.
    :param custom_error: Error type used to wrap any error coming out of
        the request.
    :return: The input call decorated to raise the desired error type.
    """

    def request_handler(*args, **kwargs):
        """Calls the unsafe function and wraps any errors coming out of it
        around a custom_error class.

        :param args: Arguments with which the function is called.
        :return: Output of the called function.
        """
        try:
            return request(*args, **kwargs)
        except requests.exceptions.SSLError as ex:
            raise custom_error(
                "Please set certificates in order to connect to the system"
            ) from ex
        except requests.exceptions.ConnectionError as ex:
            raise custom_error(
                "Could not connect to target host, please ensure connection "
                "details are correct."
            ) from ex
        except requests.exceptions.HTTPError as ex:
            raise custom_error(
                 f"Got response {ex.response.status_code} from target host."
            ) from ex
        except Exception as ex:
            raise custom_error('Failure on request to target host.') from ex

    return request_handler


class Source(AttrDict):
    """Represents a data provider within a system."""

    def __init__(self, name: str, driver: str, **kwargs):
        kwargs.setdefault('enabled', True)
        kwargs.setdefault('priority', 0)

        super().__init__(name=name, driver=driver, **kwargs)


def is_source_valid(source: Source, desired_attr: str):
    """Checks if a source can be considered valid to perform a query.

    For a source to be considered valid it must:
        * Be enabled.
        * Have the attribute passed as input.

    :param source: The source to check.
    :type source: :class:`Source`
    :param desired_attr: An attribute that is useful for performing a
        query and that is desired for the source to have.
    :type desired_attr: str
    :return: Whether the source is valid or not.
    :rtype: bool
    """
    if not source.enabled:
        return False

    if not hasattr(source, desired_attr):
        return False

    return True


def get_source_speed_score(source, func_name: str, args: Dict[str, Argument]):
    """Get the speed index for a source's method according to user input.

    :param source: Source to evaluate
    :type source: :class:`.Source`
    :param func_name: Source's method to evaluate
    :type func_name: str
    :param args: User input arguments
    :type args: dict
    """
    source_method = getattr(source, func_name)
    speed = source_method.speed_index.get('base', 0)
    for arg in args:
        speed += source_method.speed_index.get(arg, 0)
    return speed


def get_source_method(system_name: str, sources: list, func_name: str,
                      args: Dict[str, Argument]):
    """Returns a method of a single source given all the sources
    of the system and the name of function.

    :param system_name: The name of system
    :type system_name: str
    :param sources: List of Source instances
    :type sources: list[Source]
    :param func_name: The name of the function to invoke
    :type func_name: str
    :param args: User input arguments
    :type args: dict
    :raises: NoSupportedSourcesFound if no sources with the function name are
    found
    """

    speed_score = 0
    source_method = None

    for source in sources:
        if is_source_valid(source, func_name):
            source_speed_score = get_source_speed_score(source,
                                                        func_name, args)
            if source_speed_score > speed_score:
                source_method = getattr(source, func_name)
                speed_score = source_speed_score

    if not source_method:
        raise NoSupportedSourcesFound(system_name, func_name)
    LOG.debug("chose source %s with speed score %d",
              source_method.__self__.get('driver'), speed_score)

    return source_method


def speed_index(speed):
    """Add a speed index to sources methods to select the best one according to
    user input.
    """
    def decorator(func):
        setattr(func, 'speed_index', speed)
        return func
    return decorator
