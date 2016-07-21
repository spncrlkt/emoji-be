#/bin/bash

docker stop flask-$APP_NAME
docker rm flask-$APP_NAME
docker run \
  -it \
  --rm \
  --link postgres-$APP_NAME:postgres \
  --name='test' \
  -e "APP_SETTINGS=app.cfg" \
  flask-$APP_NAME \
  run_tests.py
