FROM python:3.12-slim
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
COPY app.py /app/app.py
EXPOSE 8090
CMD ["python3", "/app/app.py"]
