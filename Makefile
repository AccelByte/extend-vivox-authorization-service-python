# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

SHELL := /bin/bash

IMAGE_NAME := $(shell basename "$$(pwd)")-app
BUILDER := extend-builder

PYTHON_VERSION := 3.10

TEST_SAMPLE_CONTAINER_NAME := sample-service-extension-test

SOURCE_DIR := src
TEST_DIR := test

.PHONY: proto test

proto:
	docker run -t --rm -u $$(id -u):$$(id -g) \
		-v $$(pwd):/build \
		-w /build \
		--entrypoint /bin/bash \
		rvolosatovs/protoc:4.1.0 \
			proto.sh

build_server:

build_gateway: proto
	docker run -t --rm -u $$(id -u):$$(id -g) \
		-e GOCACHE=/data/.cache/go-cache \
		-e GOPATH=/data/.cache/go-path \
		-v $$(pwd):/data \
		-w /data/gateway \
		golang:1.20-alpine3.19 \
		go build -modcacherw -o grpc_gateway

run_server:
	docker run --rm -it -u $$(id -u):$$(id -g) \
			-e HOME=/data \
			--env-file .env \
			-v $$(pwd):/data \
			-w /data \
			--entrypoint /bin/sh \
			-p 6565:6565 \
			-p 8080:8080 \
			python:${PYTHON_VERSION}-slim \
			-c 'python -m pip install -r requirements.txt \
				&& PYTHONPATH=${SOURCE_DIR}:${TEST_DIR} python -m app'

run_gateway: proto
	docker run -it --rm -u $$(id -u):$$(id -g) \
		-e GOCACHE=/data/.cache/go-cache \
		-e GOPATH=/data/.cache/go-path \
		--env-file .env \
		-v $$(pwd):/data \
		-w /data/gateway \
		-p 8000:8000 \
		--add-host host.docker.internal:host-gateway \
		golang:1.20-alpine3.19 \
				go run main.go --grpc-addr host.docker.internal:6565

help:
	docker run --rm -t \
			-u $$(id -u):$$(id -g) \
			-v $$(pwd):/data \
			-w /data \
			-e HOME=/data \
			--entrypoint /bin/sh \
			python:${PYTHON_VERSION}-slim \
			-c 'python -m pip install -r requirements.txt \
				&& PYTHONPATH=${SOURCE_DIR}:${TEST_DIR} python -m app --help'

build: build_server build_gateway

imagex:
	docker buildx inspect $(BUILDER) || docker buildx create --name $(BUILDER) --use
	docker buildx build --tag $(IMAGE_NAME) --platform linux/amd64 .
	docker buildx build --tag $(IMAGE_NAME) --load .
	docker buildx rm --keep-state $(BUILDER)

imagex_push:
	@test -n "$(IMAGE_TAG)" || (echo "IMAGE_TAG is not set (e.g. 'v0.1.0', 'latest')"; exit 1)
	@test -n "$(REPO_URL)" || (echo "REPO_URL is not set"; exit 1)
	docker buildx inspect $(BUILDER) || docker buildx create --name $(BUILDER) --use
	docker buildx build --tag $(REPO_URL):$(IMAGE_TAG) --platform linux/amd64 --push .
	docker buildx rm --keep-state $(BUILDER)

test:
	docker run --rm -t \
			-u $$(id -u):$$(id -g) \
			-v $$(pwd):/data \
			-w /data -e HOME=/data \
			--entrypoint /bin/sh \
			python:${PYTHON_VERSION}-slim \
			-c 'python -m pip install -r requirements-dev.txt \
				&& PYTHONPATH=${SOURCE_DIR}:${TEST_DIR} python -m app_tests'

test_docs_broken_links:
	@test -n "$(SDK_MD_CRAWLER_PATH)" || (echo "SDK_MD_CRAWLER_PATH is not set" ; exit 1)
	rm -f test.err
	bash "$(SDK_MD_CRAWLER_PATH)/md-crawler.sh" \
			-i README.md
	(for FILE in $$(find docs -type f); do \
			(set -o pipefail; DOCKER_SKIP_BUILD=1 bash "$(SDK_MD_CRAWLER_PATH)/md-crawler.sh" -i $$FILE) || touch test.err; \
	done)
	[ ! -f test.err ]
