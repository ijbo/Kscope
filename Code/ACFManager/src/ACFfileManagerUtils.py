#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  3 17:51:11 2020

@author: prem
"""

import pandas as pd
import glob
import os
import shutil
import paramiko
import logging
import subprocess
log = logging.getLogger("acf")


class ACFfileManagerUtils:
    # create TX dirs. RD IU AF CO HO    
    def createTXdirs(RDpath, IUpath, AFpath, COpath, HOpath):
        os.makedirs(RDpath, exist_ok=True)
        os.makedirs(IUpath, exist_ok=True)
        os.makedirs(AFpath, exist_ok=True)
        os.makedirs(COpath, exist_ok=True)
        os.makedirs(HOpath, exist_ok=True)
        log.info("created all TX directories")

    def readBatchOfFiles(RDpath, batchsize = 50):
        #log.info("waiting for transaction files in RD directory...")
        all_files = glob.glob(os.path.join(RDpath, "*.tx"))
        if len(all_files)>0:
            return all_files
        else:
            return "no files present"

    # func to read all tx files from RD into dataframe
    def readFilesFromRDintoDF(txfilePath):
        #print("file name is : ",txfilePath)
        filename = txfilePath.split('/')[-1]

        try:
            #input - RDpath
            #RDpath = '/Volumes/personal/calsoft/ACFManager/project/RD'                     # use your path
            #all_files = glob.glob(os.path.join(RDpath, "*.tx"))     # advisable to use os.path.join as this makes concatenation OS independent
            #if len(all_files)>0:

            df_from_each_file = pd.read_csv(txfilePath, index_col = None)
            df_from_each_file.loc[0, 'tx_filename'] = filename
            log.info("(transaction) file %s are successfully read from RD directory", filename)

            #txdf['tx_filename'] = filenames
            #print(txdf)
        except Exception:
            log.exception("Error while reading tx files. Please check file, %s in RD directory...", filename)
            #return "Error while reading tx files. Please check files are present in RD directory"
            return "Error occured"
        return df_from_each_file
        
    # func to move all tx files from RD dir to IU dir
    def moveFilesFromRDtoIUAndAF(srcPath, tgtPath):
        try:
            #input - RDpath, IUpath
            #RDpath = '/Volumes/personal/calsoft/ACFManager/project/RD'                     # use your path
            #IUpath = '/Volumes/personal/calsoft/ACFManager/project/IU'                     # use your path  
            tgtPath = os.path.join(tgtPath, "")
            #os.makedirs(tgtPath, exist_ok=True)
            #all_files = glob.glob(os.path.join(srcPath, "*.tx"))     # advisable to use os.path.join as this makes concatenation OS independent
            #for file in all_files:
            shutil.move(srcPath, tgtPath)
            log.info("tx (transaction) files %s is successfully moved to IU directory", srcPath.split("/")[-1])

        except Exception:
            log.exception("error occurred while moving tx from RD to IU")
            return "file move error"
        return 'files moved'

    # func to transfer dataframe files to remote host
    # move tx files to CO dir after successful dataframe file transfer to remote host
    # move tx files to AF dir after unsuccessful dataframe file transfer to remote host
    
    def copyTxDfFilesToRemoteHost(txdf, IUpath, AFpath, COpath, archivemode):    
        
            #create ssh connection
            ssh = paramiko.SSHClient()
            ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
            #issues = False
            
            # for every tx entry move dataframe files loop
            for index, row in txdf.iterrows():
                try:
                    dataframeSourceFilePath = row['Source_file_path'] #dataframefiles path
                    remoteHost = row['Target_host']
                    remoteUser = row['target_username']
                    remotePass = row['target_pass']
                    dataframeTargetFilePath = row['Target_file_Path']
                    #ssh.connect(remoteHost, username=remoteUser, password=remotePass)
                    
                    #check archive mode as pull or push
                    if archivemode == "push":
                        # ssh.connect(remoteHost, username=remoteUser, password=remotePass)
                        # ssh.connect(remoteHost)
                        log.info("ssh connected to %s", remoteHost)
                        # sftp = ssh.open_sftp()                
                        # copy dataframe file to remote host ssh copy
                        remote_path = "/".join(dataframeTargetFilePath.rsplit("/")[:-1])
                        log.info(dataframeTargetFilePath)
                        log.info(remote_path)
                        # try:
                        #    sftp.chdir(remote_path)  # Test if remote_path exists
                        # except:
                        
                        # sftp.mkdir(remote_path)  # Create remote_path
                        # sftp.put(dataframeSourceFilePath, dataframeTargetFilePath)
                        # log.info("%s is copied to remote host",row['File_name'])
                        # sftp.close()
                        # ssh.close()
                        subprocess.check_call(["sshpass", "-p", remotePass, "ssh", remoteUser+"@"+remoteHost, 'mkdir -p', remote_path ])
                        subprocess.check_call(["sshpass", "-p", remotePass,"scp","-pr",dataframeSourceFilePath,remoteUser+"@"+remoteHost+":"+dataframeTargetFilePath])
                        
                        if row['file_tx_type'] == "mv":
                            os.remove(dataframeSourceFilePath)

                    if archivemode == "pull" and row['file_tx_type'] == "mv":
                        log.info("pulling %s file from remote server", row['File_name'])
                        subprocess.check_call(["rsync","-avz","--remove-source-files","-e","ssh",remoteHost+":"+dataframeSourceFilePath,dataframeTargetFilePath])
                        #sftp.get(dataframeremoteFilePath, dataframeSourceFilePath)
                        log.info("%s file downloaded from remote server successfully", row['File_name'])

                    if archivemode == "pull" and row['file_tx_type'] == "cp":
                        log.info("pulling %s file from remote server", row['File_name'])
                        subprocess.check_call(["rsync","-avz","-e","ssh",remoteHost+":"+dataframeSourceFilePath,dataframeTargetFilePath])
                        #sftp.get(dataframeremoteFilePath, dataframeSourceFilePath)
                        log.info("%s file downloaded from remote server successfully", row['File_name'])
                    
                    # copy tx files from IU to CO
                    if not pd.isna(row['tx_filename']):
                        srcPath = os.path.join(IUpath, row['tx_filename'])
                        tgtPath = os.path.join(COpath, row['tx_filename'])
                        shutil.move(srcPath, tgtPath)
                        log.info("tx (transaction) files %s is successfully moved to CO directory", srcPath.split("/")[-1])
        
                except Exception:
                    #issues = True
                    log.exception("error occcured while moving file %s to remote archive host", row['File_name'])
                    if not pd.isna(row['tx_filename']):
                        #copy tx files to AF dir
                        srcPath = os.path.join(IUpath, row['tx_filename'])
                        tgtPath = os.path.join(AFpath, row['tx_filename'])
                        shutil.move(srcPath, tgtPath)
                        log.info("tx (transaction) files %s is successfully moved to AF directory", srcPath.split("/")[-1])
                    continue
                    

#t = ACFfileManagerOperations()
#df = t.readFilesFromRDintoDF()
#print(df)
#print(t.moveFilesFromRDtoIUAndAF('/Volumes/personal/calsoft/ACFManager/project/RD','/Volumes/personal/calsoft/ACFManager/project/IU'))
#print(t.copyTxFilesToRemoteHost(df))
