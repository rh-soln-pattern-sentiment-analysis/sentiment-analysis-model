# sentiment-analysis

Repository for sentiment analysis related code - to be used for text analysis and part of AI/ML.

To run sentiment analysis with kafa on openshift, follow this :

Create a project in openshift
In this project create a configmap with following. You will need to change kafka bootsrap with user and password.
Also change the topics based on the ones you have created and provided R/W access to those topics with the above user/password.

1) ConfigMap in OpenShift Project :
```kind: ConfigMap
apiVersion: v1
metadata:
  name: sentiment
  namespace: sentiment
data:
  TRANSFORMERS_CACHE: /app/cache
  bootstrap_servers: <CHANGEME>:443 #Check if you need to change the port as well
  password: <CHANGEME>
  produce_topic: produce-topic # This is where the output of the model goes.
  good_language_topic: good-language-topic # This is where the reviews go based on language filter and identified as good. 
  not_good_language_topic: not-good-language-topic # This is where the reviews based on language filter and identified as not good.
  sasl_mechanism: PLAIN
  security_protocol: SASL_SSL
  topic: consume-topic # This is the topic from where the model will consume reviews for analysis. 
  langauage_topic: language-topic # This is not used for now
  username: <CHANGEME>
```

2) Create this pod and that's it.

```apiVersion: v1
kind: Pod
metadata:
  name: sentiment-analysis
spec:
  containers:
    - name: sentiment-analysis
      image: quay.io/rshah/sentiment-analysis-model:latest
      envFrom:
        - configMapRef:
            name: sentiment
```

How to check once the pod is successfully created. 
Run the following on different terminals, one to consume and other to producer. 
Ensure that you have installed kcat on your system. 
Ensure that the following variables are exported on your terminal shell.

```export KAFKA_HOST=<CHANGEME>:443
export RHOAS_SERVICE_ACCOUNT_CLIENT_ID=<CHANGEME>
export RHOAS_SERVICE_ACCOUNT_CLIENT_SECRET=<CHANGEME>
```

Ensure that you use the right topic if its difference than the one listed below.
```kcat -t consume-topic  -b "$KAFKA_HOST" \
 -X security.protocol=SASL_SSL -X sasl.mechanisms=PLAIN \
 -X sasl.username="$RHOAS_SERVICE_ACCOUNT_CLIENT_ID" \
 -X sasl.password="$RHOAS_SERVICE_ACCOUNT_CLIENT_SECRET" -P
```

On this terminal you type your message which will be consumed by model for analysis.

Ensure that you use the right topic if its difference than the one listed below.
```kcat -t produce-topic  -b "$KAFKA_HOST" \
 -X security.protocol=SASL_SSL -X sasl.mechanisms=PLAIN \
 -X sasl.username="$RHOAS_SERVICE_ACCOUNT_CLIENT_ID" \
 -X sasl.password="$RHOAS_SERVICE_ACCOUNT_CLIENT_SECRET" -C 
```

You should see the output here after analysis.

