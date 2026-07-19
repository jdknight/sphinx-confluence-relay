# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.defs import UNHEALTHY_STATUS_FLAG
import os


# flag to check if the instance should report health status events
REPORT_HEALTH_STATUS = os.getenv('SPHINX_CONFLUENCE_RELAY_HEALTH_STATUS')


def update_health_status(*, healthy: bool) -> None:
    """
    update the health status of the active service

    This call can be used to update the health status of this service.
    Primarily used for container environments to populate a "unhealthy"
    file flag.

    Args:
        healthy: flag to indicate service is healthy
    """

    # if managing a health status (e.g. for docker), ensure flag is created
    # or removed
    if REPORT_HEALTH_STATUS:
        if healthy:
            if UNHEALTHY_STATUS_FLAG.is_file():
                UNHEALTHY_STATUS_FLAG.unlink()
        else:
            UNHEALTHY_STATUS_FLAG.parent.mkdir(parents=True, exist_ok=True)
            UNHEALTHY_STATUS_FLAG.touch()
