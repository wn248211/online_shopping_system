#
# Janky front-end to bring some sanity (?) to the litany of tools and switches
# in setting up, tearing down and validating your Minikube cluster for working
# with k8s and istio.
#
# This file covers off building the Docker images and optionally running them
#
# The intended approach to working with this makefile is to update select
# elements (body, id, IP, port, etc) as you progress through your workflow.
# Where possible, stodout outputs are tee into .out files for later review.
#
# Switch to alternate container registry by setting CREG accordingly.
#
# This script is set up for Github's newly announced (and still beta) container
# registry to side-step DockerHub's throttling of their free accounts.
# If you wish to switch back to DockerHub, CREG=docker.io
#
# TODO: You must run the template processor to fill in the template variables "ZZ-*"
#

CREG=ZZ-CR-ID
REGID=ZZ-REG-ID

DK=docker

# Keep all the logs out of main directory
LOG_DIR=logs

all: order db

deploy: order db
	$(DK) run -t --publish 5002:5002 --detach --name order $(CREG)/$(REGID)/cmpt756pj-order:v1 | tee order.svc.log
	$(DK) run -t \
		-e AWS_REGION="ZZ-AWS-REGION" \
		-e AWS_ACCESS_KEY_ID="ZZ-AWS-ACCESS-KEY-ID" \
		-e AWS_SECRET_ACCESS_KEY="ZZ-AWS-SECRET-ACCESS-KEY" \
		-e AWS_SESSION_TOKEN="ZZ-AWS-SESSION-TOKEN" \
            --publish 5003:5003 --detach --name db $(CREG)/$(REGID)/cmpt756pj-db:v1 | tee db.svc.log

scratch:
	$(DK) stop `$(DK) ps -a -q --filter name="db"` | tee db.stop.log
	$(DK) stop `$(DK) ps -a -q --filter name="order"` | tee order.stop.log

clean:
	rm $(LOG_DIR)/{order,db}.{img,repo,svc}.log

order: $(LOG_DIR)/order.repo.log

db: $(LOG_DIR)/db.repo.log

$(LOG_DIR)/order.repo.log: order/app.py order/Dockerfile
	$(DK) build -t $(CREG)/$(REGID)/cmpt756pj-order:v1 order | tee $(LOG_DIR)/order.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-order:v1 | tee $(LOG_DIR)/order.repo.log

$(LOG_DIR)/db.repo.log: db/Dockerfile
	$(DK) build -t $(CREG)/$(REGID)/cmpt756pj-db:v1 db | tee $(LOG_DIR)/db.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-db:v1 | tee $(LOG_DIR)/db.repo.log
