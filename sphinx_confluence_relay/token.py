# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sphinx_confluence_relay.settings import SettingsDep
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from secrets import compare_digest
from typing import Annotated


security = HTTPBearer(
    # tailored authentication
    auto_error=False,
)

# provides a security instance which fastapi can use with dependency injection
SecurityDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]


def verify_token(
        credentials: SecurityDep,
        settings: SettingsDep,
        space_key: str | None = None,
    ) -> None:
    """
    token validation for requests

    Publish endpoints can be configured for authentication. If the instance
    is configured with a token to restrict access, it will be checked to
    ensure it exists in the request before processing a route.

    Args:
        credentials: the credentials to check
        settings: the application settings
        space_key: the space_key (if available)

    Raises:
        HTTPException: if authentication has failed
    """

    publish_tokens = settings.publish_tokens

    # check if this a restricted call with a space key options; if so, check
    # if we have space-specific token to check against
    if space_key and settings.space_tokens.get(space_key):
        publish_tokens = settings.space_tokens[space_key]
    # ignore if no token is configured
    elif not settings.publish_tokens:
        return

    # if no credentials are provided from the user, deny
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='no token provided',
        )

    # verify token is valid
    authorized = False

    for token in publish_tokens:
        if compare_digest(credentials.credentials, token):
            authorized = True
            break

    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='invalid/expired token',
        )
