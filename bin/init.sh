#/bin/bash

source ./ENV

echo -n "U REALLY WANNA INIT THE APP ?(y/n)?"

read answer
if echo "$answer" | grep -iq "^y" ;then
  ./postgres/bin/build_data_vol.sh
  ./postgres/bin/restart.sh
  ./app/bin/create_dbs.sh
  ./app/bin/build.sh && ./app/bin/restart.sh
else
    echo "fine then i wont u mfer"
fi

