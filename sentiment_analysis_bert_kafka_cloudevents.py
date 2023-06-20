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
from cloudevents.http import CloudEvent
from cloudevents.http import from_http
from cloudevents.conversion import to_binary
import requests

TRANSFORMERS_CACHE = os.environ['TRANSFORMERS_CACHE']
bootstrap_servers = os.environ['bootstrap_servers']
username = os.environ['username']
password = os.environ['password']
sasl_mechanism = os.environ['sasl_mechanism']
security_protocol = os.environ['security_protocol']
topic = os.environ['topic']
reviews_sentiment_sink = os.environ['reviews_sentiment_sink']
attributes = {
    "type": os.environ['ce_type'],
    "source": os.environ['ce_source']
}

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
#    value_deserializer=lambda m: json.loads(m.decode('utf-8'))    
)




# Load the BERT model and tokenizer
model_name = 'nlptown/bert-base-multilingual-uncased-sentiment'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# Start consuming Kafka messages
print("Entering for loop")
for message in consumer:
    try:    
        # Get the text message from the Kafka message
        print("message.value", message.value)
        print("message.headers", message.headers)
        json_payload = message.value
        # Parse the CloudEvent from the JSON payload
        sentiment_data =  json.loads(json_payload)
        
        try:
            review_text = sentiment_data['review_text']
        except KeyError:
            print("Not valid data input syntax")
        except ValueError:
            print("NULL text")
            continue
        inputs = tokenizer(review_text, padding=True, truncation=True, max_length=512, return_tensors='pt')
        inputs = inputs.to(device)

        # Use the BERT model to predict the text being abusive and if yes, then send that to another kafka topic for moderation
        outputs = model(**inputs)
        predictions = torch.softmax(outputs.logits, dim=1).detach().cpu().numpy()
        sentiment = int(predictions.argmax(axis=1)[0]) - 1  # Convert 0-4 to -1-3
        response = f"{'positive' if sentiment > 0 else 'negative' if sentiment < 0 else 'neutral'}"

        # Capture language analysis output as sentiment
        sentiment_data['score'] = sentiment
        sentiment_data['response'] = response
        json_string = json.dumps(sentiment_data)
        
        event = CloudEvent({ "type": "reviews-sentiment-event", "source": "reviews-sentiment" }, sentiment_data)
        headers, body = to_binary(event)


        print("sentiment score is [" + str(sentiment) + "]")

        requests.post(reviews_sentiment_sink, data=body, headers=headers)

    except json.JSONDecodeError:
        print("Non-JSON message received, skipping...")
    except KeyError:
        print("Missing fields in JSON message, skipping...")
