# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from fastapi import APIRouter
from fastapi import Request
from fastapi import status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from sphinx_confluence_relay.settings import SettingsDep


# router for part number creation-related content
router = APIRouter()


@router.get('/', include_in_schema=False)
async def root_swagger(
        req: Request,
        settings: SettingsDep,
    ) -> HTMLResponse:
    rsp = get_swagger_ui_html(
        openapi_url=req.app.openapi_url,
        title='Sphinx Confluence Relay',
        swagger_js_url='/static/vendor/swagger-ui-bundle.js',
        swagger_css_url='/static/vendor/swagger-ui.css',
        swagger_favicon_url='/static/favicon.png',
    )

    content = bytes(rsp.body).decode('utf-8')

    # inject our custom css modifications
    custom_css = '<link rel="stylesheet" href="/static/scr.css">'
    content = content.replace('</head>', f'{custom_css}\n</head>')

    # inject a banner
    if settings.banner:
        banner = f'<header class="scr-banner">{settings.banner}</header>'
        content = content.replace('<body>', f'<body>\n{banner}')

    return HTMLResponse(content=content, status_code=status.HTTP_200_OK)
