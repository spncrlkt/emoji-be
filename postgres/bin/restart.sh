docker stop postgres-$APP_NAME
docker rm postgres-$APP_NAME
docker run \
  --name postgres-$APP_NAME \
  -d \
  --volumes-from postgres-data-$APP_NAME \
  postgres:9.5.3

