#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 19:38:16 2020

@author: prem
"""


import jsoncfg
import os

class readConfigFile:
    def __init__(self, configFilePath):
        # create config parser
        self.config = jsoncfg.load_config(configFilePath)
                
    def getRDPath(self):
        return os.path.join(self.config.tx.txrootpath(), self.config.tx.txfilepaths.RDpath(), "")

    def getIUPath(self):
        return os.path.join(self.config.tx.txrootpath(), self.config.tx.txfilepaths.IUpath(), "")

    def getAFPath(self):
        return os.path.join(self.config.tx.txrootpath(), self.config.tx.txfilepaths.AFpath(), "")

    def getCOPath(self):
        return os.path.join(self.config.tx.txrootpath(), self.config.tx.txfilepaths.COpath(), "")

    def getHOPath(self):
        return os.path.join(self.config.tx.txrootpath(), self.config.tx.txfilepaths.HOpath(), "")

    def getAllLoggingInfo(self):
        return self.config.logging()

    def getMaxProcesses(self):
        return self.config.MaxProcesses()

    def getArchiveMode(self):
        return self.config.archivemode()
        
#config = readConfigFile("config/config.cfg")
#print(config.getAllLoggingInfo())
#cf = readConfigFile("config/config")

