# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

# type of image to build
# - local: builds using a local package, already prepared (python -m build)
# - external: builds using pypi's available version of sphinx-confluence-relay
ARG BUILD_MODE=external

# base image
FROM alpine:latest AS base

# prepare required python environment
RUN apk add --no-cache python3 py3-pip tzdata uvicorn
RUN python -m venv /opt/sphinx-confluence-relay/venv
ENV PATH="/opt/sphinx-confluence-relay/venv/bin:$PATH"

# build steps for processing a local build
FROM base AS build_local
RUN pip install build
COPY . /build
WORKDIR /build
RUN cd /build &&\
    python -m build &&\
    cp dist/*.whl / &&\
    rm -rf /build

# build steps for processing an external build
FROM base AS build_external
RUN pip download --dest / sphinx-confluence-relay

FROM build_${BUILD_MODE}
RUN ls -al /

# final image
FROM build_${BUILD_MODE} AS final
RUN pip install /*.whl && rm /*.whl

# configure default command
COPY --chmod=744 docker/docker-cmd.sh /run/docker-cmd.sh

# configure to report a unhealthy status
ENV SPHINX_CONFLUENCE_RELAY_HEALTH_STATUS=1

CMD [ "/run/docker-cmd.sh" ]

HEALTHCHECK --interval=60s --timeout=3s --retries=1 \
    CMD [ ! -f /run/sphinx-confluence-relay/unhealthy ] || exit 1
