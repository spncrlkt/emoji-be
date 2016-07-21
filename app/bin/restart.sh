docker stop flask-$APP_NAME
docker rm flask-$APP_NAME
docker run \
  -d \
  -p 5000:5000 \
  --name flask-$APP_NAME \
  --link postgres-$APP_NAME:postgres \
  -e "APP_SETTINGS=app.cfg" \
  flask-$APP_NAME
