SHELL=/bin/bash
PYTHON=python3

IMAGE=aws-mmg-cw-logs
NAME=aws-mmg-cw-logs
VERSION=$(shell . $(RELEASE_SUPPORT) ; getVersion)
TAG=$(shell . $(RELEASE_SUPPORT); getTag)
RELEASE_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-release-support
DOCKER_HUB=docker.io

DEFAULT_REGION=eu-central-1

S3_BUCKET_PREFIX=aws-mmg-cw-logs
S3_BUCKET=$(S3_BUCKET_PREFIX)-$(DEFAULT_REGION)

ACCOUNT_NUMBER=$(shell aws sts get-caller-identity --query Account --output text)
AWS_PROFILE=
AWS_REGION=

ECR_REPO=$(ACCOUNT_NUMBER).dkr.ecr.$(DEFAULT_REGION).amazonaws.com

ALL_REGIONS=$(shell aws --region $(DEFAULT_REGION) \
		ec2 describe-regions 		\
		--query 'join(`\n`, Regions[?RegionName != `$(DEFAULT_REGION)`].RegionName)' \
		--output text)

help:
	# @echo 'make				-	build zip file to target/.'
	@echo 'make release		- build zip file and uploads to S3'
	@echo 'make clean		- deletes virtual environment and target'
	@echo 'make deploy		-  builds zip file to target/ and deploys lambda source code to $(S3_BUCKET)'
	@echo 'make deploy-all	- deploys lambda source code to all regions with prefix $(S3_BUCKET_PREFIX)'
	@echo 'make deploy-cfn  - deploys cfn stack'
	@echo 'make delete-cfn  - deletes cfn stack'

# release: build push .release check-status check-release
release:build push .release

.release:
	@echo "release=0.0.0" > .release
	@echo "tag=$(NAME)-0.0.0" >> .release
	@echo INFO: .release created
	@cat .release

showversion: .release
	@. $(RELEASE_SUPPORT); getVersion

tag: TAG$(shell . $(RELEASE_SUPPORT); getTag $(VERSION))
# tag: check-status
tag:
	@. $(RELEASE_SUPPORT) ; ! tagExists $(TAG) || (echo "ERROR: tag $(TAG) for version $(VERSION) already tagged in git" >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; setRelease $(VERSION)
	git add .
	git commit -m "bumped to version $(VERSION)" ;
	git tag $(TAG) ;
	@if [ -n "$(shell git remote -v)" ] ; then git push && git push --tags ; fi

# check-status:
# 	@. $(RELEASE_SUPPORT) ; ! hasChanges || (echo "ERROR: there are still changes" >&2 && exit 1) ;


build: .release
	@if [[ -f Dockerfile ]]; then \
		docker build -t $(IMAGE):$(VERSION) . ; \
	else echo "No Dockerfile in this repo" > /dev/null ; \
	fi

# CMD_REPOLOGIN := "eval $$\( aws ecr"
# ifdef AWS_PROFILE
# CMD_REPOLOGIN += " --profile $(AWS_PROFILE)"
# endif
# ifdef AWS_CLI_REGION
# CMD_REPOLOGIN += " --region $(DEFAULT_REGION)"
# endif
# CMD_REPOLOGIN += " get-login-password --region $(DEFAULT_REGION) \| docker login --username AWS --password-stdin $(ACCOUNT_NUMBER).dkr.ecr.$(DEFAULT_REGION).amazonaws.com \)"

# ecr-login:
# 	@eval $(CMD_REPOLOGIN)
# push: ecr-login push-latest push-version
push:
	@if [[ -f Dockerfile ]]; then \
		docker push $(IMAGE):$(VERSION) ; \
		docker push $(IMAGE):latest ; \
	else echo > /dev/null ; \
	fi
# push-latest: tag
# 	@echo "upload latest to $(ECR_REPO)"
# 	@if [[ -f Dockerfile ]]; then \
# 	docker push $(ECR_REPO)/$(NAME):latest
# 	else echo > /dev/null ; \
# 	fi
# push-version: tag-version
# 	@echo "upload $(VERSION) to $(ECR_REPO)"

target/$(NAME)-$(VERSION).zip: setup.py src/*/*.py requirements.txt Dockerfile.lambda
	mkdir -p target
	rm -rf dist/* target/*
	pipenv run python setup.py check
	pipenv run python setup.py build
	pipenv run python setup.py sdist
	docker build --build-arg ZIPFILE=$(NAME)-$(VERSION).zip -t $(NAME)-lambda:$(VERSION) -f Dockerfile.lambda . && \
		ID=$$(docker create $(NAME)-lambda:$(VERSION) /bin/true) && \
		docker export $$ID | (cd target && tar -xvf - $(NAME)-$(VERSION).zip) && \
		docker rm -f $$ID && \
		chmod ugo+r target/$(NAME)-$(VERSION).zip

Pipfile.lock: Pipfile requirements.txt test-requirements.txt setup.py
	pipenv update -d

deploy: target/$(NAME)-$(VERSION).zip
	aws s3 --region $(DEFAULT_REGION) \
		cp --acl public-read target/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip
	aws s3 --region $(DEFAULT_REGION) \
		cp --acl public-read \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-latest.zip


deploy-all: deploy
	@for REGION in $(ALL_REGIONS); do \
		aws s3 --region $$REGION \
			cp --acl public-read \
			s3://$(S3_BUCKET_PREFIX)-$(DEFAULT_REGION)/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip; \
		aws s3 --region $$REGION \
			cp  --acl public-read \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-latest.zip; \

deploy-cfn: deploy target/$(NAME)-$(VERSION).zip
