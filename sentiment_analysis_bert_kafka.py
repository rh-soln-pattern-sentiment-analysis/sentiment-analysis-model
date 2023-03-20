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

TRANSFORMERS_CACHE = os.environ['TRANSFORMERS_CACHE']
bootstrap_servers = os.environ['bootstrap_servers']
topic = os.environ['topic']
produce_topic = os.environ['produce_topic']
username = os.environ['username']
password = os.environ['password']
sasl_mechanism = os.environ['sasl_mechanism']
security_protocol = os.environ['security_protocol']

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
    timestamp = timestamp.strftime("%m/%d/%Y, %H:%M:%S")
    text = message.value.decode('utf-8')
    # May need to use this later - customer_id, product_id, review_text = text.split(",")
    # Tokenize the text message
    inputs = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors='pt')
    inputs = inputs.to(device)

    # Use the BERT model to predict the sentiment
    outputs = model(**inputs)
    predictions = torch.softmax(outputs.logits, dim=1).detach().cpu().numpy()
    sentiment = int(predictions.argmax(axis=1)[0]) - 1  # Convert 0-4 to -1-3
    customer_id = 1023
    product_id = 1
    data = {}
    data['sentiment'] = sentiment
    data['text-comment'] = text
    response = f"{'positive' if sentiment > 0 else 'negative' if sentiment < 0 else 'neutral'}"
    data['response'] = response    
    json_data = json.dumps(data)
    json_string = json.dumps({'timestamp': timestamp, 'customer_id': customer_id,'product_id': product_id,'sentiment': sentiment,'text': text,'response': response})
    producer.send(produce_topic, json_string.encode('utf-8')) 