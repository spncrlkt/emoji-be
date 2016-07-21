#/bin/bash

source ./ENV

./postgres/bin/restart.sh
./app/bin/build.sh && ./app/bin/restart.sh
