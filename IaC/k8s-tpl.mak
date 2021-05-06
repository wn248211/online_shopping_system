#
# Front-end to bring some sanity to the litany of tools and switches
# for working with a k8s cluster. Note that this file exercise core k8s
# commands that's independent of the cluster vendor.
#
# All vendor-specific commands are in the make file for that vendor:
# az.mak, eks.mak, gcp.mak, mk.mak
#
# This file addresses APPPLing the Deployment, Service, Gateway, and VirtualService
#
# Be sure to set your context appropriately for the log monitor.
#
# The intended approach to working with this makefile is to update select
# elements (body, id, IP, port, etc) as you progress through your workflow.
# Where possible, stodout outputs are tee into .out files for later review.

# These will be filled in by template processor
CREG=ZZ-CR-ID
REGID=ZZ-REG-ID
AWS_REGION=ZZ-AWS-REGION
JAVA_HOME=ZZ-JAVA-HOME
GAT_DIR=ZZ-GAT-DIR

# Keep all the logs out of main directory
LOG_DIR=logs

# These should be in your search path
KC=kubectl
DK=docker
AWS=aws
IC=istioctl

# Application versions
# Override these by environment variables and `make -e`
APP_VER_TAG=v1
ORDER_VER=v1
LOADER_VER=v1

# Gatling parameters to be overridden by environment variables and `make -e`
SIM_NAME=ReadUserSim
USERS=1

# Gatling parameters that most of the time will be unchanged
# but which you might override as projects become sophisticated
SIM_FILE=ReadTables.scala
SIM_PACKAGE=proj756
GATLING_OPTIONS=

# Other Gatling parameters---you should not have to change these
GAT=$(GAT_DIR)/bin/gatling.sh
SIM_DIR=gatling/simulations
RES_DIR=gatling/resources
SIM_PACKAGE_DIR=$(SIM_DIR)/$(SIM_PACKAGE)
SIM_FULL_NAME=$(SIM_PACKAGE).$(SIM_NAME)

# Kubernetes parameters that most of the time will be unchanged
# but which you might override as projects become sophisticated
APP_NS=c756ns
ISTIO_NS=istio-system

# ----------------------------------------------------------------------------------------
# -------  Targets to be invoked directly from command line                        -------
# ----------------------------------------------------------------------------------------

# ---  templates:  Instantiate all template files
#
# This is the only entry that *must* be run from k8s-tpl.mak
# (because it creates k8s.mak)
templates:
	tools/process-templates.sh

# --- provision: Provision the entire stack
# This typically is all you need to do to install the sample application and
# all its dependencies
#
# Preconditions:
# 1. Templates have been instantiated (make -f k8s-tpl.mak templates)
# 2. Current context is a running Kubernetes cluster (make -f {az,eks,gcp,mk}.mak start)
#
provision: istio prom kiali deploy

# --- deploy: Deploy and monitor the three microservices
# Use `provision` to deploy the entire stack (including Istio, Prometheus, ...).
# This target only deploys the sample microservices
deploy: appns gw user item order db monitoring
	$(KC) -n $(APP_NS) get gw,vs,deploy,svc,pods

# --- rollout: Rollout new deployments of all microservices
rollout: rollout-user rollout-item rollout-order rollout-db

# --- rollout-user: Rollout a new deployment of user
rollout-user: user
	$(KC) rollout -n $(APP_NS) restart deployment/cmpt756pj-user

# --- rollout-user: Rollout a new deployment of user
rollout-item: $(LOG_DIR)/item.repo.log  cluster/item-dpl.yaml
	$(KC) -n $(APP_NS) apply -f cluster/item-dpl.yaml | tee $(LOG_DIR)/rollout-item.log
	$(KC) rollout -n $(APP_NS) restart deployment/cmpt756pj-item | tee -a $(LOG_DIR)/rollout-item.log

# --- rollout-order: Rollout a new deployment of order
rollout-order: $(LOG_DIR)/order-$(ORDER_VER).repo.log  cluster/order-dpl-$(ORDER_VER).yaml
	$(KC) -n $(APP_NS) apply -f cluster/order-dpl-$(ORDER_VER).yaml | tee $(LOG_DIR)/rollout-order.log
	$(KC) rollout -n $(APP_NS) restart deployment/cmpt756pj-order-$(ORDER_VER) | tee -a $(LOG_DIR)/rollout-order.log

# --- rollout-db: Rollout a new deployment of DB
rollout-db: db
	$(KC) rollout -n $(APP_NS) restart deployment/cmpt756pj-db

# --- health-off: Turn off the health monitoring for the three microservices
# If you don't know exactly why you want to do this---don't
health-off:
	$(KC) -n $(APP_NS) apply -f cluster/user-nohealth.yaml
	$(KC) -n $(APP_NS) apply -f cluster/item-nohealth.yaml
	$(KC) -n $(APP_NS) apply -f cluster/order-nohealth.yaml
	$(KC) -n $(APP_NS) apply -f cluster/db-nohealth.yaml

# --- scratch: Delete the microservices and everything else in application NS
scratch: clean
	$(KC) delete -n $(APP_NS) deploy --all
	$(KC) delete -n $(APP_NS) svc    --all
	$(KC) delete -n $(APP_NS) gw     --all
	$(KC) delete -n $(APP_NS) dr     --all
	$(KC) delete -n $(APP_NS) vs     --all
	$(KC) delete -n $(APP_NS) se     --all
	$(KC) delete -n $(ISTIO_NS) vs monitoring --ignore-not-found=true
	$(KC) get -n $(APP_NS) deploy,svc,pods,gw,dr,vs,se
	$(KC) get -n $(ISTIO_NS) vs

# --- clean: Delete all the application log files
clean:
	/bin/rm -f $(LOG_DIR)/{user,item,order,db,gw,monvs}*.log $(LOG_DIR)/rollout*.log

# --- dashboard: Start the standard Kubernetes dashboard
# NOTE:  Before invoking this, the dashboard must be installed and a service account created
dashboard: showcontext
	echo Please follow instructions at https://docs.aws.amazon.com/eks/latest/userguide/dashboard-tutorial.html
	echo Remember to 'pkill kubectl' when you are done!
	$(KC) proxy &
	open http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#!/login

# --- extern: Display status of Istio ingress gateway
# Especially useful for Minikube, if you can't remember whether you invoked its `lb`
# target or directly ran `minikube tunnel`
extern: showcontext
	$(KC) -n $(ISTIO_NS) get svc istio-ingressgateway

# --- log-X: show the log of a particular service
log-user:
	$(KC) -n $(APP_NS) logs deployment/cmpt756pj-user --container cmpt756pj-user

log-item:
	$(KC) -n $(APP_NS) logs deployment/cmpt756pj-item --container cmpt756pj-item

log-order:
	$(KC) -n $(APP_NS) logs deployment/cmpt756pj-order --container cmpt756pj-order

log-db:
	$(KC) -n $(APP_NS) logs deployment/cmpt756pj-db --container cmpt756pj-db


# --- shell-X: hint for shell into a particular service
shell-user:
	@echo Use the following command line to drop into the user service:
	@echo   $(KC) -n $(APP_NS) exec -it deployment/cmpt756pj-user --container cmpt756pj-user -- bash

shell-item:
	@echo Use the following command line to drop into the item service:
	@echo   $(KC) -n $(APP_NS) exec -it deployment/cmpt756pj-item --container cmpt756pj-item -- bash

shell-order:
	@echo Use the following command line to drop into the order service:
	@echo   $(KC) -n $(APP_NS) exec -it deployment/cmpt756pj-order --container cmpt756pj-order -- bash

shell-db:
	@echo Use the following command line to drop into the db service:
	@echo   $(KC) -n $(APP_NS) exec -it deployment/cmpt756pj-db --container cmpt756pj-db -- bash

# --- lsa: List services in all namespaces
lsa: showcontext
	$(KC) get svc --all-namespaces

# --- ls: Show deploy, pods, vs, and svc of application ns
ls: showcontext
	$(KC) get -n $(APP_NS) gw,vs,svc,deployments,pods

# --- lsd: Show containers in pods for all namespaces
lsd:
	$(KC) get pods --all-namespaces -o=jsonpath='{range .items[*]}{"\n"}{.metadata.name}{":\t"}{range .spec.containers[*]}{.image}{", "}{end}{end}' | sort

# --- reinstate: Reinstate provisioning on a new set of worker nodes
# Do this after you do `up` on a cluster that implements that operation.
# AWS implements `up` and `down`; other cloud vendors may not.
reinstate: istio
	$(KC) create ns $(APP_NS) | tee $(LOG_DIR)/reinstate.log
	$(KC) label ns $(APP_NS) istio-injection=enabled | tee -a $(LOG_DIR)/reinstate.log

# --- showcontext: Display current context
showcontext:
	$(KC) config get-contexts

# Run the loader, rebuilding if necessary, starting DynamDB if necessary, building ConfigMaps
loader: dynamodb-init $(LOG_DIR)/loader.repo.log cluster/loader.yaml
	$(KC) -n $(APP_NS) delete --ignore-not-found=true jobs/cmpt756pj-loader
	tools/build-configmap.sh $(RES_DIR)/user.csv cluster/user-header.yaml | kubectl -n $(APP_NS) apply -f -
	tools/build-configmap.sh $(RES_DIR)/item.csv cluster/item-header.yaml | kubectl -n $(APP_NS) apply -f -
	tools/build-configmap.sh $(RES_DIR)/order.csv cluster/order-header.yaml | kubectl -n $(APP_NS) apply -f -
	$(KC) -n $(APP_NS) apply -f cluster/loader.yaml | tee $(LOG_DIR)/loader.log

# --- dynamodb-init: set up our DynamoDB tables
#
dynamodb-init: $(LOG_DIR)/dynamodb-init.log

# --- dynamodb-stop: Stop the AWS DynamoDB service
#
dynamodb-clean:
	$(AWS) cloudformation delete-stack --stack-name db-team-ZZ-REG-ID || true | tee $(LOG_DIR)/dynamodb-clean.log
	@# Rename DynamoDB log so dynamodb-init will force a restart but retain the log
	/bin/mv -f $(LOG_DIR)/dynamodb-init.log $(LOG_DIR)/dynamodb-init-old.log

# --- ls-tables: List the tables and their read/write units for all DynamodDB tables
ls-tables:
	@tools/list-dynamodb-tables.sh $(AWS) $(AWS_REGION)

# --- registry-login: Login to the container registry
#
registry-login:
	# Use '@' to suppress echoing the $CR_PAT to screen
	@/bin/sh -c 'echo ${CR_PAT} | $(DK) login $(CREG) -u $(REGID) --password-stdin'

# --- Variables defined for URL targets
# Utility to get the hostname (AWS) or ip (everyone else) of a load-balanced service
# Must be followed by a service
IP_GET_CMD=tools/getip.sh $(KC) $(ISTIO_NS)

# This expression is reused several times
# Use back-tick for subshell so as not to confuse with make $() variable notation
INGRESS_IP=`$(IP_GET_CMD) svc/istio-ingressgateway`

# --- kiali-url: Print the URL to browse Kiali in current cluster
kiali-url:
	@/bin/sh -c 'echo http://$(INGRESS_IP)/kiali'

# --- grafana-url: Print the URL to browse Grafana in current cluster
grafana-url:
	@# Use back-tick for subshell so as not to confuse with make $() variable notation
	@/bin/sh -c 'echo http://`$(IP_GET_CMD) svc/grafana-ingress`:3000/'

# --- prometheus-url: Print the URL to browse Prometheus in current cluster
prometheus-url:
	@# Use back-tick for subshell so as not to confuse with make $() variable notation
	@/bin/sh -c 'echo http://`$(IP_GET_CMD) svc/prom-ingress`:9090/'

# --- Variables defined for Gatling targets
#
# Suffix to all Gatling commands
# 2>&1:       Redirect stderr to stdout. This ensures the long errors from a
#             misnamed Gatling script are clipped
# | head -18: Display first 18 lines, discard the rest
# &:          Run in background
GAT_SUFFIX=2>&1 | head -18 &

# --- gatling-command: Print the bash command to run a Gatling simulation
# Less convenient than gatling-music or gatling-user (below) but the resulting commands
# from this target are listed by `jobs` and thus easy to kill.
gatling-command:
	@/bin/sh -c 'echo "CLUSTER_IP=$(INGRESS_IP) USERS=1 SIM_NAME=ReadMusicSim make -e -f k8s.mak run-gatling $(GAT_SUFFIX)"'

# ----------------------------------------------------------------------------------------
# ------- Targets called by above. Not normally invoked directly from command line -------
# ------- Note that some subtargets are in `obs.mak`                               -------
# ----------------------------------------------------------------------------------------

# Install Prometheus stack by calling `obs.mak` recursively
prom:
	make -f obs.mak init-helm
	make -f obs.mak install-prom

# Install Kiali operator and Kiali by calling `obs.mak` recursively
# Waits for Kiali to be created and begin running. This wait is required
# before installing the three microservices because they
# depend upon some Custom Resource Definitions (CRDs) added
# by Kiali
kiali:
	make -f obs.mak install-kiali
	# Kiali operator can take awhile to start Kiali
	tools/waiteq.sh 'app=kiali' '{.items[*]}'              ''        'Kiali' 'Created'
	tools/waitne.sh 'app=kiali' '{.items[0].status.phase}' 'Running' 'Kiali' 'Running'

# Install Istio
istio:
	$(IC) install --set profile=demo --set hub=gcr.io/istio-release | tee -a $(LOG_DIR)/mk-reinstate.log

# Create and configure the application namespace
appns:
	# Appended "|| true" so that make continues even when command fails
	# because namespace already exists
	$(KC) create ns $(APP_NS) || true
	$(KC) label namespace $(APP_NS) --overwrite=true istio-injection=enabled

# Update monitoring virtual service and display result
monitoring: monvs
	$(KC) -n $(ISTIO_NS) get vs

# Update monitoring virtual service
monvs: cluster/monitoring-virtualservice.yaml
	$(KC) -n $(ISTIO_NS) apply -f $< > $(LOG_DIR)/monvs.log

# Update service gateway
gw: cluster/service-gateway.yaml
	$(KC) -n $(APP_NS) apply -f $< > $(LOG_DIR)/gw.log

# Start DynamoDB at the default read and write rates
$(LOG_DIR)/dynamodb-init.log: cluster/cloudformationdynamodb.json
	@# "|| true" suffix because command fails when stack already exists
	@# (even with --on-failure DO_NOTHING, a nonzero error code is returned)
	$(AWS) cloudformation create-stack --stack-name db-team-ZZ-REG-ID --template-body file://$< || true | tee $(LOG_DIR)/dynamodb-init.log

# Update user and associated monitoring, rebuilding if necessary
user: $(LOG_DIR)/user.repo.log cluster/user.yaml cluster/user-sm.yaml cluster/user-vs.yaml
	$(KC) -n $(APP_NS) apply -f cluster/user.yaml | tee $(LOG_DIR)/user.log
	$(KC) -n $(APP_NS) apply -f cluster/user-sm.yaml | tee -a $(LOG_DIR)/user.log
	$(KC) -n $(APP_NS) apply -f cluster/user-vs.yaml | tee -a $(LOG_DIR)/user.log

# Update item and associated monitoring, rebuilding if necessary
item: rollout-item cluster/item-svc.yaml cluster/item-sm.yaml cluster/item-vs.yaml
	$(KC) -n $(APP_NS) apply -f cluster/item-svc.yaml | tee $(LOG_DIR)/item.log
	$(KC) -n $(APP_NS) apply -f cluster/item-sm.yaml | tee -a $(LOG_DIR)/item.log
	$(KC) -n $(APP_NS) apply -f cluster/item-vs.yaml | tee -a $(LOG_DIR)/item.log

# Update order and associated monitoring, rebuilding if necessary
order: rollout-order cluster/order-svc.yaml cluster/order-sm.yaml cluster/order-vs-$(ORDER_VER).yaml
	$(KC) -n $(APP_NS) apply -f cluster/order-svc.yaml | tee $(LOG_DIR)/order.log
	$(KC) -n $(APP_NS) apply -f cluster/order-sm.yaml | tee -a $(LOG_DIR)/order.log
	$(KC) -n $(APP_NS) apply -f cluster/order-vs-$(ORDER_VER).yaml | tee -a $(LOG_DIR)/order.log

# Update DB and associated monitoring, rebuilding if necessary
db: $(LOG_DIR)/db.repo.log cluster/awscred.yaml cluster/dynamodb-service-entry.yaml cluster/db.yaml cluster/db-sm.yaml cluster/db-vs.yaml
	$(KC) -n $(APP_NS) apply -f cluster/awscred.yaml | tee $(LOG_DIR)/db.log
	$(KC) -n $(APP_NS) apply -f cluster/dynamodb-service-entry.yaml | tee -a $(LOG_DIR)/db.log
	$(KC) -n $(APP_NS) apply -f cluster/db.yaml | tee -a $(LOG_DIR)/db.log
	$(KC) -n $(APP_NS) apply -f cluster/db-sm.yaml | tee -a $(LOG_DIR)/db.log
	$(KC) -n $(APP_NS) apply -f cluster/db-vs.yaml | tee -a $(LOG_DIR)/db.log

# Build & push the images up to the CR
cri: $(LOG_DIR)/user.repo.log $(LOG_DIR)/item.repo.log $(LOG_DIR)/order-$(ORDER_VER).repo.log $(LOG_DIR)/db.repo.log

# Build the user service
$(LOG_DIR)/user.repo.log: ../code/user/Dockerfile ../code/user/app.py ../code/user/requirements.txt
	$(DK) build -t $(CREG)/$(REGID)/cmpt756pj-user:$(APP_VER_TAG) ../code/user | tee $(LOG_DIR)/user.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-user:$(APP_VER_TAG) | tee $(LOG_DIR)/user.repo.log

# Build the item service
$(LOG_DIR)/item.repo.log: ../code/item/Dockerfile ../code/item/app.py ../code/item/requirements.txt
	$(DK) build -t $(CREG)/$(REGID)/cmpt756pj-item:$(APP_VER_TAG) ../code/item | tee $(LOG_DIR)/item.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-item:$(APP_VER_TAG) | tee $(LOG_DIR)/item.repo.log

# Build the order service
$(LOG_DIR)/order-$(ORDER_VER).repo.log: ../code/order/Dockerfile ../code/order/app.py ../code/order/requirements.txt
	$(DK) build -t $(CREG)/$(REGID)/cmpt756pj-order:$(ORDER_VER) ../code/order | tee $(LOG_DIR)/order.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-order:$(ORDER_VER) | tee $(LOG_DIR)/order-$(ORDER_VER).repo.log

# Build the db service
$(LOG_DIR)/db.repo.log: ../code/db/Dockerfile ../code/db/app.py ../code/db/requirements.txt
	$(DK) build -t $(CREG)/$(REGID)/cmpt756pj-db:$(APP_VER_TAG) ../code/db | tee $(LOG_DIR)/db.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-db:$(APP_VER_TAG) | tee $(LOG_DIR)/db.repo.log

# Build the loader
$(LOG_DIR)/loader.repo.log: ../code/loader/app.py ../code/loader/requirements.txt ../code/loader/Dockerfile
	$(DK) image build -t $(CREG)/$(REGID)/cmpt756pj-loader:$(LOADER_VER) loader  | tee $(LOG_DIR)/loader.img.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-loader:$(LOADER_VER) | tee $(LOG_DIR)/loader.repo.log

# Push all the container images to the container registry
# This isn't often used because the individual build targets also push
# the updated images to the registry
cr:
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-user:$(APP_VER_TAG) | tee $(LOG_DIR)/user.repo.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-item:$(APP_VER_TAG) | tee $(LOG_DIR)/item.repo.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-order:$(ORDER_VER) | tee $(LOG_DIR)/order.repo.log
	$(DK) push $(CREG)/$(REGID)/cmpt756pj-db:$(APP_VER_TAG) | tee $(LOG_DIR)/db.repo.log

#
# Other attempts at Gatling commands. Target `gatling-command` is preferred.
# The following may not even work.
#
# General Gatling target: Specify CLUSTER_IP, USERS, and SIM_NAME as environment variables. Full output.
run-gatling:
	JAVA_HOME=$(JAVA_HOME) $(GAT) -rsf $(RES_DIR) -sf $(SIM_DIR) -bf $(GAT_DIR)/target/test-classes -s $(SIM_FULL_NAME) -rd "Simulation $(SIM_NAME)" $(GATLING_OPTIONS)

# The following should probably not be used---it starts the job but under most shells
# this process will not be listed by the `jobs` command. This makes it difficult
# to kill the process when you want to end the load test
gatling-order:
	@/bin/sh -c 'CLUSTER_IP=$(INGRESS_IP) USERS=$(USERS) SIM_NAME=ReadOrderSim JAVA_HOME=$(JAVA_HOME) $(GAT) -rsf $(RES_DIR) -sf $(SIM_DIR) -bf $(GAT_DIR)/target/test-classes -s $(SIM_FULL_NAME) -rd "Simulation $(SIM_NAME)" $(GATLING_OPTIONS) $(GAT_SUFFIX)'

# Different approach from gatling-music but the same problems. Probably do not use this.
gatling-user:
	@/bin/sh -c 'CLUSTER_IP=$(INGRESS_IP) USERS=$(USERS) SIM_NAME=ReadUserSim make -e -f k8s.mak run-gatling $(GAT_SUFFIX)'

gatling-item:
	@/bin/sh -c 'CLUSTER_IP=$(INGRESS_IP) USERS=$(USERS) SIM_NAME=ReadItemSim make -e -f k8s.mak run-gatling $(GAT_SUFFIX)'


# ---------------------------------------------------------------------------------------
# Handy bits for exploring the container images... not necessary
image: showcontext
	$(DK) image ls | tee __header | grep $(REGID) > __content
	head -n 1 __header
	cat __content
	rm __content __header
