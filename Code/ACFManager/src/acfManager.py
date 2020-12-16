#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 19:47:27 2020

@author: prem
"""

# Include standard modules
from ACFfileManagerUtils import ACFfileManagerUtils

class acfManager:
    def __init__(self, RDpath, IUpath, AFpath, COpath, HOpath, archivemode):
        self.RDpath = RDpath
        self.IUpath = IUpath
        self.AFpath = AFpath
        self.COpath = COpath
        self.HOpath = HOpath
        self.archivemode = archivemode

    def runInitialTXdirs(self):
        return ACFfileManagerUtils.createTXdirs(self.RDpath, self.IUpath, self.AFpath, self.COpath, self.HOpath)

    def runReadBatchOfTxFiles(self):
        return ACFfileManagerUtils.readBatchOfFiles(self.RDpath)

    def runAcfOperations(self, txfilePath):
        return ACFfileManagerUtils.readFilesFromRDintoDF(txfilePath)

    def runMoveTxToIU(self, txfilePathRD):
        return ACFfileManagerUtils.moveFilesFromRDtoIUAndAF(txfilePathRD, self.IUpath)

    def runArchiveDFfilesWithTxFiles(self, txdf):
        return ACFfileManagerUtils.copyTxDfFilesToRemoteHost(txdf, self.IUpath, self.AFpath, self.COpath, self.archivemode)