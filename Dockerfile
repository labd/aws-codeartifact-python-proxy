FROM python:3.10-slim

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3"]
CMD ["app.py"]
EXPOSE 5000
