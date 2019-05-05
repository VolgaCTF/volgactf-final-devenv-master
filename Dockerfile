FROM python:3.6-alpine
ADD src VERSION /dist/
WORKDIR /dist
RUN apk add --update build-base libffi-dev openssl-dev && pip install -r requirements.txt
CMD ["gunicorn", "app:app", "--reload", "--worker-class", "gevent", "--bind", "0.0.0.0:80"]
EXPOSE 80
