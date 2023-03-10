FROM python:3.9

RUN mkdir /app
WORKDIR /app
RUN mkdir /app/cache
ENV TRANSFORMERS_CACHE=/app/cache/
COPY * /app
RUN chmod -R 755 /app/cache
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN chmod +x /app/*
CMD ["python", "/app/sentiment_analysis_bert_kafka.py"]