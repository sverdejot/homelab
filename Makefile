.DEFAULT_GOAL := help

.PHONY: help build-docker push-docker

ACT_IMAGE = "sverdejot/act"

help:
	@echo "Available targets:"
	@awk -F':|##' \
		'/^[^\t].+?:.*?##/ && !/^[[:space:]]*__/{\
			printf "\033[36m%-30s\033[0m %s\n", $$1, $$NF \
		}' $(MAKEFILE_LIST)

build-docker: # Build CI runner image and push to DockerHub
	@docker build -f build/act/Dockerfile -t $(ACT_IMAGE):latest .

push-docker: build-docker
	@docker push $(ACT_IMAGE):latest

