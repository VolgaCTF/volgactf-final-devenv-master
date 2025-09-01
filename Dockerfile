FROM node:24-alpine AS assets
ADD package.json package-lock.json /app/
WORKDIR /app
RUN npm ci && mkdir -p ./src/static && npm run build

FROM python:3.13-alpine
LABEL maintainer="VolgaCTF"

ARG BUILD_DATE
ARG BUILD_VERSION
ARG VCS_REF

LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.name="volgactf-final-devenv-master"
LABEL org.label-schema.description="VolgaCTF Final devenv master – provides a Dockerfile for a devenv core application (master)"
LABEL org.label-schema.url="https://volgactf.ru/en"
LABEL org.label-schema.vcs-url="https://github.com/VolgaCTF/volgactf-final-devenv-master"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.version=$BUILD_VERSION

ADD src VERSION /dist/
COPY --from=assets /app/src/static/bootstrap.min.css /dist/static/
WORKDIR /dist
RUN apk add --update build-base libffi-dev openssl-dev && pip install -r requirements.txt
#CMD ["gunicorn", "app:app", "--reload", "--worker-class", "gevent", "--bind", "0.0.0.0:80"]
CMD ["python", "server.py"]
EXPOSE 80
