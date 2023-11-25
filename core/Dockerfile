FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . /app
RUN chmod +x /app/entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/app/entrypoint.sh"]