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
from ssl import SSLContext, PROTOCOL_TLSv1

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
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))    
)

# Set up a Kafka producer
producer = KafkaProducer(
    bootstrap_servers=bootstrap_servers,
    sasl_plain_username=username,
    sasl_plain_password=password,
    security_protocol=security_protocol,
    sasl_mechanism=sasl_mechanism,
    value_serializer=lambda m: json.dumps(m).encode('utf-8')    
)

# Load the BERT model and tokenizer
model_name = 'nlptown/bert-base-multilingual-uncased-sentiment'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

for message in consumer:
    try:
        # Get the text message from the Kafka message
        print(message)
        sentiment_data = message.value
        product_id = sentiment_data["product_id"]
#        customer_id = sentiment_data["user"]["customer_id"]
        browser = sentiment_data["user"]["browser"]
        region = sentiment_data["user"]["region"]
        review_text = sentiment_data["review_text"]
        print("Review Text Message BEING PRINTED")
        print(review_text)    
        inputs = tokenizer(review_text, padding=True, truncation=True, max_length=512, return_tensors='pt')
        inputs = inputs.to(device)

        # Use the BERT model to predict the sentiment
        outputs = model(**inputs)
        predictions = torch.softmax(outputs.logits, dim=1).detach().cpu().numpy()
        sentiment = int(predictions.argmax(axis=1)[0]) - 1  # Convert 0-4 to -1-3
        data = {}
        data['sentiment'] = sentiment
        data['review_text'] = review_text
        response = f"{'positive' if sentiment > 0 else 'negative' if sentiment < 0 else 'neutral'}"
        data['response'] = response    
        json_data = json.dumps(data)
        json_string = json.dumps({'sentiment': sentiment, 'product_id': product_id, 'browser': browser, 'region': region, 'review_text': review_text,'response': response})
        print(json_string)  
        producer.send(produce_topic, json_string)    
    except json.JSONDecodeError:
        print("Non-JSON message received, skipping...")
    except KeyError:
        print("Missing fields in JSON message, skipping...")   