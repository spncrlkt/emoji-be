#/bin/bash

source ./ENV

docker stop flask-$APP_NAME && docker rm flask-$APP_NAME
docker stop postgres-$APP_NAME && docker rm postgres-$APP_NAME
