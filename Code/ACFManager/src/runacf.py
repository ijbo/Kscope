import argparse
from ACFfileManagerUtils import ACFfileManagerUtils
from ReadConfigACF import readConfigFile
import pandas
import logging.config
import multiprocessing
import time
from multiprocessing import Pool
import os
from acfManager import acfManager
    
def worker_process(filenamebatch):
    root.info("process %s started...", os.getpid())
    for filename in filenamebatch:
        txdf = acf.runAcfOperations(filename)
        if type(txdf)==pandas.core.frame.DataFrame and txdf.shape[0] > 0:
            acf.runMoveTxToIU(filename)
            acf.runArchiveDFfilesWithTxFiles(txdf)
            del txdf
    root.info("process %s finished...", os.getpid())


def scaleFileBatches(filesset):
    global noOfBatches
    global instancesToUse
    batchsets = []
    
    if (len(filesset) <= batchsize):
        for file in filesset:
            templist = []
            templist.append(file)
            batchsets.append(templist)
        return batchsets
    else:
        start = 0
        end = start+batchsize
        noOfBatches = (len(filesset)//batchsize)+1
        if noOfBatches>maxProcesses:
            instancesToUse = maxProcesses
        else:
            instancesToUse = noOfBatches

        for _ in range(noOfBatches):
            filesbatch = filesset[start:end]
            start = end
            end = start+batchsize
            if len(filesbatch)>0:
                batchsets.append(filesbatch)
        #print(batchsets)
        return batchsets
    
def startMultiprocessing(filebatch):
    with Pool(instancesToUse) as p:
        p.map(worker_process, filebatch)
                
def acfstart():
    global root
    
    while 1:
        root.info("waiting for files...")
        time.sleep(5)
        RDfilesSet = acf.runReadBatchOfTxFiles()
        if type(RDfilesSet) == str and RDfilesSet == "no files present":
            continue
        else:              
            startMultiprocessing(scaleFileBatches(RDfilesSet))

if __name__ == "__main__":
    # Initiate the parser
    parser = argparse.ArgumentParser(description="Run ACFManager process")
    parser.add_argument("configpath", help="provide config file path", type=str)

    # Read arguments from the command line
    args = parser.parse_args()

    # Check for --version or -V
    config = readConfigFile(args.configpath)

    #config = readConfigFile("./config/config.cfg")
    
    logging.config.dictConfig(dict(config.getAllLoggingInfo()))
    root = logging.getLogger("acf")
    batchsize = 10
    maxProcesses = config.getMaxProcesses()
    instancesToUse = batchsize
    noOfBatches = 1
    acf = acfManager(config.getRDPath(), config.getIUPath(),
                    config.getAFPath(), config.getCOPath(), config.getHOPath(), config.getArchiveMode())
    acf.runInitialTXdirs()
    acfstart()