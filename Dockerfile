# Copyright (c) 2025 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

# ----------------------------------------
# Stage 1: Protoc Code Generation
# ----------------------------------------
FROM --platform=$BUILDPLATFORM rvolosatovs/protoc:v7.0.0 AS proto-builder

# Set working directory.
WORKDIR /build

# Copy proto sources and generator script.
COPY proto.sh .
COPY proto/ proto/

# Make script executable and run it.
RUN chmod +x proto.sh && \
    ./proto.sh



# ----------------------------------------
# Stage 2: gRPC Gateway Builder
# ----------------------------------------
FROM --platform=$BUILDPLATFORM golang:1.26 AS grpc-gateway-builder

ARG TARGETOS
ARG TARGETARCH

ARG GOOS=$TARGETOS
ARG GOARCH=$TARGETARCH
ARG CGO_ENABLED=0

# Set working directory.
WORKDIR /build

# Copy gateway go module files.
COPY gateway/go.mod gateway/go.sum ./

# Download dependencies.
RUN go mod download

# Copy application code.
COPY gateway/ .

# Copy generated protobuf files from stage 1.
RUN rm -rf pkg/pb
COPY --from=proto-builder /build/gateway/pkg/pb ./pkg/pb

# Build application code.
RUN go build -v -o /output/$TARGETOS/$TARGETARCH/grpc_gateway .



# ----------------------------------------
# Stage 3: gRPC Server Builder
# ----------------------------------------
FROM ubuntu:26.04 AS grpc-server-builder

ARG TARGETOS
ARG TARGETARCH

# Keeps Python from generating .pyc files in the container.
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging.
ENV PYTHONUNBUFFERED=1

# Install Python.
RUN apt update && \
    apt install -y --no-install-recommends \
        python3-venv && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd user

# Set working directory.
WORKDIR /build

# Create and activate virtual environment.
RUN python3 -m venv venv
ENV PATH="/build/venv/bin:$PATH"

# Install Python dependencies.
COPY requirements.txt .
RUN python3 -m pip install \
    --no-cache-dir \
    --requirement requirements.txt

# Copy apidocs code from stage 1.
COPY --from=proto-builder /build/gateway/apidocs ./apidocs

# Copy gateway code from stage 2.
COPY --from=grpc-gateway-builder /output/$TARGETOS/$TARGETARCH/grpc_gateway ./

# Copy other gateway code.
COPY gateway/third_party third_party/

# Copy application code.
COPY src/ .

# Copy generated protobuf files from stage 1.
COPY --from=proto-builder /build/src/ .

# Copy entrypoint script.
COPY wrapper.sh .
RUN chmod +x wrapper.sh

# Fix up python3 symlink for use in chiseled Ubuntu.
RUN ln -sf /usr/bin/python3 /build/venv/bin/python3 



# ----------------------------------------
# Stage 4: Runtime Container
# ----------------------------------------
FROM ubuntu/python:3.14-26.04_stable

# Keeps Python from generating .pyc files in the container.
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging.
ENV PYTHONUNBUFFERED=1

# Set working directory.
WORKDIR /app

# Copy build from stage 2.
COPY --from=grpc-server-builder /usr/bin/bash /usr/bin/bash
COPY --from=grpc-server-builder /usr/bin/kill /usr/bin/kill
COPY --from=grpc-server-builder /usr/bin/sleep /usr/bin/sleep
# The 26.04 chiseled image ships a minimal library set. Pull in what the
# copied binaries and wheels need at runtime:
#   libstdc++                          -> grpcio's _cython extension
#   libsystemd, libselinux, libpcre2-8 -> coreutils `sleep`, used by wrapper.sh
COPY --from=grpc-server-builder \
    /usr/lib/*-linux-gnu/libstdc++.so.6* \
    /usr/lib/*-linux-gnu/libsystemd.so.0* \
    /usr/lib/*-linux-gnu/libselinux.so.1* \
    /usr/lib/*-linux-gnu/libpcre2-8.so.0* \
    /usr/lib/
COPY --from=grpc-server-builder /etc/passwd /etc/passwd
COPY --from=grpc-server-builder /etc/group /etc/group
COPY --from=grpc-server-builder /build/ .

USER user

# Activate virtual environment.
ENV PATH="/app/venv/bin:$PATH"

# Plugin Arch gRPC Server Port.
EXPOSE 6565

# gRPC Gateway Port.
EXPOSE 8000

# Prometheus /metrics Web Server Port.
EXPOSE 8080

# Entrypoint.
ENTRYPOINT ["bash", "/app/wrapper.sh"]
