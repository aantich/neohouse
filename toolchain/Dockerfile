# SPDX-License-Identifier: MIT
ARG BASE_IMAGE=debian@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc
FROM ${BASE_IMAGE} AS dependencies

ARG DEBIAN_SNAPSHOT=20261110T000000Z
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
       "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/ bookworm main" \
       "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/ bookworm-security main" \
       > /etc/apt/sources.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       autoconf automake binutils build-essential ca-certificates file \
       libffi-dev libgmp-dev libncurses-dev libnuma-dev libtinfo5 \
       pkg-config python3 xz-utils \
    && rm -rf /var/lib/apt/lists/*

FROM dependencies AS compiler
COPY toolchain/lock.json /opt/house-toolchain/lock.json
COPY .cache/ghc-9.14.1-i386-deb10-linux.tar.xz /tmp/ghc.tar.xz
RUN python3 -c 'import hashlib,json; p="/tmp/ghc.tar.xz"; expected=json.load(open("/opt/house-toolchain/lock.json"))["compiler"]["sha256"]; actual=hashlib.file_digest(open(p,"rb"),"sha256").hexdigest(); assert actual == expected, (actual,expected)' \
    && mkdir /opt/ghc \
    && tar -xJf /tmp/ghc.tar.xz -C /opt/ghc --strip-components=1 \
    && cd /opt/ghc \
    && ./configure --prefix=/opt/ghc \
    && make lib/settings \
    && cp mk/system-cxx-std-lib-1.0.conf lib/package.conf.d/ \
    && bin/ghc-pkg --global-package-db /opt/ghc/lib/package.conf.d recache \
    && rm /tmp/ghc.tar.xz \
    && dpkg-query -W -f='${binary:Package}\t${Version}\n' > /opt/house-toolchain/debian-packages.tsv

ENV PATH="/opt/ghc/bin:${PATH}"
WORKDIR /work
RUN ghc --numeric-version && ghc --info > /opt/house-toolchain/ghc-info.txt
