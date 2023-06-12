FROM python:3.9

RUN mkdir /app
WORKDIR /app
RUN mkdir -p /app/cache
ENV TRANSFORMERS_CACHE=/app/cache/
COPY * /app
RUN chown -R 1001:0 /app\
&&  chmod -R og+rwx /app \
&&  chmod -R +x /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt
CMD ["python", "/app/sentiment_analysis_bert_kafka_cloudevents.py"]
