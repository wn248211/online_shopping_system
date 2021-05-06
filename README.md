# Online shopping system
CMPT 756's term project.
Our application is an online shopping system. It is designed for users to place orders online, manage items in their shopping cart, checkout their shopping cart, which turns it into an order, and list their orders.


# Deploment
### **Instantiate the templates**  
Refer to the subdirectory ***IaC***. Copy the file cluster/tpl-vars-blank.txt to cluster/tpl-vars.txt and fill in all the required values in tpl-vars.txt, run  
```
$ make -f k8s-tpl.mak templates
```

### **Setup DynamoDB tables**
Run the following command from the ***IaC/cluster*** folder:
```
aws cloudformation create-stack --stack-name db-teamw --template-body file://cloudformationdynamodb.json
```


### **Start a new cluster**
Refer to the directory ***IaC*** and create a new cluster by running
```
$ make -f VENDOR.mak start
```
where VENDOR is one of mk (Minikube), az (Azure), eks (Amazon), or gcp (Google).

### **Provision the cluster**
Provision it with the single command:
```
$ make -f k8s.mak provision
```


# Coverage Simulation
Run the following command from directory ***IaC***.  
For order service
```
tools/gatling.sh 1 CreateAndReadOrderSim
```
For user service
```
tools/gatling.sh 1 CreateAndReadUserSim
```
For item service
```
tools/gatling.sh 1 CreateAndReadItemSim
```
When completed, you can get the report from directory IaC/gatling/results

# Laod Simulation

### **Start the Gatling test**
Run the following command from directory ***IaC***
```
tools/gatling.sh 50 LoadSim
```
The load simulation will last 10 minutes. When completed, you can get the report from directory ***IaC/gatling/results***

### **Observation**
Print the Grafana URL
```
make -f k8s.mak grafana-url
```
Print the Kiali URL
```
make -f k8s.mak kiali-url
```

# Failure Analysis
1. Simulate machine failure by deleting a pod of db service.
```
# enter IaC directory
cd IaC

# Run load simulation of 10 users
tools/gatling.sh 10 LoadSim

# list all resources and find one of the pod of db service
make -f k8s.mak ls

# delete the pod of db service, db_pod_name is found in the previous step
kubectl delete {db_pod_name}
```

2. Check Grafana dashboard. Error rate occurs when pod is deleted, and disappears when the pod is recovered.

3. Fix deployment yaml file by changing `replicas=1` to `replicas=2`.

4. Deploy db service
```
make -f k8s.mak rollout-db
```

5. Retry machine failure simulation (step 1). Check Grafana dashboard. No error occurs in the process of pod recovery.
