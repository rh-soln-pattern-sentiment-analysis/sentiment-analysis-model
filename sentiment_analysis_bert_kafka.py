from kafka.consumer import KafkaConsumer
from kafka.producer import KafkaProducer
from kafka.errors import KafkaError
from transformers import pipeline
import ssl
import json
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from datetime import datetime

# On one screen try this in a terminal window to generate messages. Ensure that kcat is installed to test this manually.
# kcat -t consume-topic  -b "$KAFKA_HOST" \
# -X security.protocol=SASL_SSL -X sasl.mechanisms=PLAIN \
# -X sasl.username="$RHOAS_SERVICE_ACCOUNT_CLIENT_ID" \
# -X sasl.password="$RHOAS_SERVICE_ACCOUNT_CLIENT_SECRET" -P
#Testing doesnt look good
#Is this really worth!

# On another screen try this to get the output from another topic
# kcat -t produce-topic  -b "$KAFKA_HOST" \
# -X security.protocol=SASL_SSL -X sasl.mechanisms=PLAIN \
# -X sasl.username="$RHOAS_SERVICE_ACCOUNT_CLIENT_ID" \
# -X sasl.password="$RHOAS_SERVICE_ACCOUNT_CLIENT_SECRET" -C
#Testing doesnt look good (negative)
#Is this really worth! (positive)
#% Reached end of topic produce-topic [0] at offset 2

bootstrap_servers = ['XXXXXXXXXX.kafka.rhcloud.com:443']
topic = 'consume-topic'
produce_topic = 'produce-topic'
username = 'XXXXXXXXXX'
password = 'XXXXXXXXXX'
sasl_mechanism = 'PLAIN'
security_protocol = 'SASL_SSL'

# Set up a Kafka consumer
consumer = KafkaConsumer(
    topic,
    bootstrap_servers=bootstrap_servers,
    sasl_plain_username=username,
    sasl_plain_password=password,
    security_protocol=security_protocol,
    sasl_mechanism=sasl_mechanism,
    auto_offset_reset='latest',
    enable_auto_commit=True,
)

# Set up a Kafka producer
producer = KafkaProducer(
    bootstrap_servers=bootstrap_servers,
    sasl_plain_username=username,
    sasl_plain_password=password,
    security_protocol=security_protocol,
    sasl_mechanism=sasl_mechanism
)

# Load the BERT model and tokenizer
model_name = 'nlptown/bert-base-multilingual-uncased-sentiment'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# Start consuming Kafka messages
for message in consumer:
    # Get the text message from the Kafka message
    timestamp = datetime.fromtimestamp(message.timestamp/1000.0)
    print(timestamp)
    text = message.value.decode('utf-8')
    print(text)
    # Tokenize the text message
    inputs = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors='pt')
    inputs = inputs.to(device)

    # Use the BERT model to predict the sentiment
    outputs = model(**inputs)
    predictions = torch.softmax(outputs.logits, dim=1).detach().cpu().numpy()
    sentiment = int(predictions.argmax(axis=1)[0]) - 1  # Convert 0-4 to -1-3
    customer_id = 1023
    product_id = 1
    sentiment_output = f"{customer_id},{product_id},{sentiment}" 
    # Produce a response message with the sentiment
    response_message = f"{timestamp} {customer_id},{product_id}, {text} ({'positive' if sentiment > 0 else 'negative' if sentiment < 0 else 'neutral'})"
    producer.send(produce_topic, response_message.encode('utf-8'))