#!/bin/bash
for i in "$@"
do
case $i in
    -c=*|--colletion_time=*)
    CollectionTime="${i#*=}"
    ;;
    -s=*|--steps=*)
    Steps="${i#*=}"
    ;;
    -i=*|--instance_id=*)
    InstanceID="${i#*=}"
    ;;
    -r=*|--config_path=*)
    CfgPath="${i#*=}"
    ;;
    --default)
    DEFAULT=YES
    ;;
    *)
            # unknown option
    ;;
esac
done

ScriptName="collection.py"
cmd="/usr/local/Anaconda3-5.1.0-Linux-x86_64/envs/automate_rftool/bin/python app/$ScriptName" 
default_config="/home/web/calsoft/V5/config/rfdfCollector_default.cfg"
echo "$InstanceID"
if [ ! -z "$InstanceID" ]
then
   cmd="${cmd} -i $InstanceID"
else
   echo "Please provide InstanceId with -i flag"
   exit  
fi

if [ ! -z "$CfgPath" ]
then
   if [ -e "$CfgPath" ]
   then
        cmd="${cmd} -r $CfgPath"
        out=`jq '.' $CfgPath >/dev/null 2>&1`
        if [ $? -eq 0 ]; then
             echo ''
        else
             echo "JSONParseError: Invalid Json in $CfgPath"
        fi
   else 
       echo "FileNotFoundError: $CfgPath not found"
   fi   
else
  if [ -e "$default_config" ]
   then
        cmd="${cmd} -r $default_config"
        out=`jq '.' $default_config >/dev/null 2>&1`
        if [ $? -eq 0 ]; then
             echo "Taking default config file $default_config"
        else
             echo "JSONParseError: Invalid Json in $default_config File"
        fi
   else
       echo "FileNotFoundError: $default_config= not found"
   fi
fi

if [ ! -z  "$Steps" ]
then
   cmd="${cmd} -s $Steps"
fi
if [ ! -z "$CollectionTime" ]
then
   cmd="${cmd} -c $CollectionTime"
fi
echo $cmd

$cmd


# /usr/local/Anaconda3-5.1.0-Linux-x86_64/envs/automate_rftool/bin/python /home/web/calsoft/V3/$ScriptName -i $InstanceID -r $CfgPath -s $Steps
