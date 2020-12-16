import json
import warnings
from datetime import datetime
import os
import multiprocessing as mp
import time
import logging
from customLogHandlers import CustomFileHandler
from listenerProcess import runListener
from configParser import AcquirerConfig
from pydantic import ValidationError
from requests.packages import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def getJson(config_path):
    data = {}
    with open(config_path, "r") as f:
        data = json.load(f)
    print(data)
    return data

def configBatch(config, listener_caption):
    _batch_list = []
    x=0     
    for i in range(0, len(config.iDRACS), config.batch_size):
        batch_obj = dict()
        batch_obj["iDRACS"] = config.iDRACS[i:i + config.batch_size]
        batch_obj["port"] = str(config.ports_list[x]) 
        batch_obj["file_collection_time"] = config.file_collection_time
        batch_obj["file_collection_path"] = config.file_collection_path
        batch_obj["listener_name"] = listener_caption + "_" + batch_obj["port"]
        _batch_list.append(batch_obj)
        x=x+1
    return _batch_list

def acquirerMP(batch_list, logger):
    q = mp.Queue()
    jobs = [] 
    for batch in batch_list:
        p = mp.Process(name=batch['listener_name'], target=runListener, args=(batch, q,))
        jobs.append(p)
        p.start()
  
    while True:
        if not q.empty():
            msg = q.get_nowait()
            # check = msg.split("|")[-1].strip()
            msg_list = msg.split("|")
            if msg_list[-1] != "Available":
                logger.info(msg)

    for job in jobs:
        job.join()


    
def set_logger(config_data):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    print(config_data.log_file_path)
    log_file_name= f"{config_data.log_file_path}/rfacquire_{timestamp}.log"
    # logging.basicConfig(filename=logname,filemode='a',level=logging.DEBUG)
    logger = logging.getLogger('rfacquire')
    logger.setLevel(logging.DEBUG)
    
    fh = CustomFileHandler(log_file_name, maxBytes=int(config_data.log_file_size))
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger
  
    # print(q.qsize(),"<---Qsize")
    # count = 0
    # dictCounter= Defaulrdict()  {all_idrac: 0}
    # while not q.empty():
        # print("reading",q.empty())
        # switches 
        # print(q.get(),"<--Queue Detail")
        # getIP from Queue and append  IP as key and value is 1 in defaultDict_A()  
        # Increment counter . count++
        # if count == 10,000:
        # make counter = 0
        # Merge dictCounter and defaultDict_A and create defaultDictC
        # check defautDictC with 0 value and add in log with error message "{idrac_ip}| Unavailable"
        #     check if ip_addr.err is exists then ok else create err file with 0 byte and with name ip_addr.err. 
        # check defautDictC with 1 value then check file exists . if exists then rename it to ipaddr_old.err and add in log error message "{idrac_ip}| Unavailable"
        # 
        # print("reading",q.empty())

def createOutputFolders(folders):
    for folder in folders:
        if not os.path.exists(f"{folder}"):
            os.makedirs(f"{folder}")

if __name__ == "__main__":
    config_path = "config/configAcquirer.cfg"
    config_data = getJson(config_path)
    listener_caption = "listener"
    try:
        config=AcquirerConfig(**config_data)
        logger = set_logger(config)
        batch_list = configBatch(config, listener_caption)
        
        createOutputFolders([f"{config.file_collection_path}/output", f"{config.file_collection_path}/complete"])
        # print("Batch List are ", batch_list)
        acquirerMP(batch_list, logger)        
    except ValidationError as err:
        print(err)


