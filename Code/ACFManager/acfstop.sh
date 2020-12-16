echo "stopping acf manager process..."
#pgrep -f "sh acfstart.sh"
#pgrep -f "python /home/web/project/src/acfManager.py /home/web/project/config/config.cfg"
ps -ef | grep 'sh acfstart.sh' | grep -v grep | awk '{print $2}' | xargs -r kill -9
echo "acf manager process stopped..."
 
