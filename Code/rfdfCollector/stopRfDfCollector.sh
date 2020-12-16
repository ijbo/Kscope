#!/bin/sh

#Find the Process ID for syncapp running instance

for i in "$@"
do
case $i in
    -i=*|--config_path=*)
    InstanceID="${i#*=}"
    ;;
    --default)
    DEFAULT=YES
    ;;
    *)
            # unknown option
    ;;
esac
done



PID=`ps -eaf | grep "InstanceId $InstanceID" | grep -v grep | awk '{print $2}'`
if [[ "" !=  "$PID" ]]; then
  echo "killing $PID"
  kill -9 $PID
fi
