import os, signal
import hashlib
import glob
import copy
import time
import uuid
import csv
import json
import random
import psutil
import shutil
import argparse
from configuration import FactoryProducer
import setproctitle as spt
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

class Collection(ABC):
    dataframe_path = None
    metadata_path = None
    step_size = None
    params = None
    cfg_data = None
    tx_header = [["sys_creation_date", "sys_update_date", "File_name", "Source_host", "Target_host", "Source_file_path", "Target_file_Path", "file_tx_type","target_username","target_pass"]]
    base_data_path  = "../rfDataframe/data"
    archieve_path = "/home/web/calsoft/archieve/"
    # base_data_path  = "/home/web/calsoft/data"

    @classmethod
    @abstractmethod
    def collect(cls, params, collector_cfg_data):
        cls.setter(params, collector_cfg_data)
        cls.set_directories(collector_cfg_data)
        if collector_cfg_data["collectorParams"]["recoveryMode"].lower() == 'on':
            cls.recover()

    @classmethod
    def config_creation(cls, cfg_data, steps=None):
        cfg_data["job"]["executionMode"]["endTime"] = str(cls.end_time) 
        cfg_data["job"]["executionMode"]["startTime"] = str(cls.start_time)
        rfdataframe_json_path = cls.create_rfdataframe_config(cfg_data)
        return rfdataframe_json_path
        
    @classmethod
    def create_tx_df_entry(cls, dataframe_name):
        return [str(datetime.now()), str(datetime.now()), dataframe_name,
                "192.168.12.228", "192.168.12.228", os.path.join(cls.cfg_data["collectorParams"]["rfdftempPath"], dataframe_name),
                os.path.join(cls.archieve_path, "dataframes", dataframe_name), cls.cfg_data["archiveStorage"]["fileOperation"],"web", "web"]

    @classmethod
    def create_tx_metadata_entry(cls, metadata_name):
        return [str(datetime.now()), str(datetime.now()), metadata_name,
                "192.168.12.228", "192.168.12.228", os.path.join(cls.cfg_data["collectorParams"]["rfdftempPath"], metadata_name),
                os.path.join(cls.archieve_path, "metadata", metadata_name), cls.cfg_data["archiveStorage"]["fileOperation"],"web", "web"]
        
    @classmethod
    def move_files(cls, destination):
        entries = []
        df_files = glob.glob(f"{cls.dataframe_path}/*")
        for f in df_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_df_entry(f))
        meta_files = glob.glob(f"{cls.metadata_path}/*")
        for f in meta_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_metadata_entry(f))
        cls.make_entry_RD("dataframes_{}.tx".format(str(uuid.uuid4())), entries)


    @classmethod
    def invoke_rfDataframe(cls, config_name):
        # print("df called", config_name)
        os.system(" docker exec -it rfdataframe_c node rfDataframe --rfdf-config {}".format(config_name))

    @classmethod
    def recover_move_files(cls, dataframe_path, metadata_path, destination):
        entries = []
        df_files = glob.glob(f"{dataframe_path}/*")
        for f in df_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_df_entry(f))
        meta_files = glob.glob(f"{metadata_path}/*")
        for f in meta_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_metadata_entry(f))
        cls.make_entry_RD("dataframes_{}.tx".format(str(uuid.uuid4())), entries)

    @classmethod
    def recover(cls):
        print("Recovering the old dataframes")
        path= f"{cls.base_data_path}/{cls.instance_id}"
        process_ids = os.listdir(path)        
        for process_id in process_ids:
            dataframe_path = f"{path}/{process_id}/dataframes" 
            metadata_path  =  f"{path}/{process_id}/metadata"
            destination  =  f"{path}/{process_id}/temp"
            cls.recover_move_files(dataframe_path,metadata_path, destination)

    @classmethod
    def _make_directories(cls, base_path, folder_name):
        try:
            os.makedirs(os.path.join(base_path, folder_name))
        except:
            pass
        return os.path.join(base_path, folder_name)
    
    @classmethod
    def _make_rfdataframe_config(cls, cfg_data):
        _config_json = {}
        for key in ['job', 'database', 'redfish']:
            _config_json[key] = cfg_data[key]
        return _config_json

    @classmethod
    def write_json(cls, cfg_data, config_name, config_json):
        config_path = cfg_data["collectorParams"]["customConfig"]
        with open(os.path.join(config_path, config_name), "w") as jsonFile:
            json.dump(config_json, jsonFile, indent=4)

    @classmethod
    def create_rfdataframe_config(cls, cfg_data):
        _name_pattern = "config_{}.json"
        _config_json = cls._make_rfdataframe_config(cfg_data)
        _config_name = _name_pattern.format(random.randint(1, 100000))
        cls.write_json(cfg_data, _config_name, _config_json)
        return os.path.join("config", cfg_data["collectorParams"]["runningInstanceId"]["Instance_Id"],
                                      str(cfg_data["collectorParams"]["runningInstanceId"]["Process_Id"]),
                                       _config_name)

    @classmethod
    def _calculate_datetime(cls, unit, value, date_time):
        if unit == "mi":
            return date_time + timedelta(minutes=int(value))    
        elif unit == "hh":
            return date_time + timedelta(hours=int(value))     
        elif unit == "dd":
            return date_time + timedelta(days=int(value))
        else:
            pass
    
    @classmethod
    def _get_datetime(self, date_time, format, replace=False):
        if replace:
            return datetime.strptime(str(date_time.replace(microsecond=0)), format)    
        return datetime.strptime(str(date_time), format)

    @classmethod
    def set_directories(cls, collector_cfg_data):
        dataframes_base_path =  "/".join(collector_cfg_data["collectorParams"]["rfdftempPath"].rsplit("/")[:-1])
        cls.dataframe_path = cls._make_directories(dataframes_base_path, 'dataframes')
        cls.metadata_path = cls._make_directories(dataframes_base_path, 'metadata')
        cls._make_directories(dataframes_base_path, 'tmp')

    @classmethod
    def setter(cls, params, collector_cfg_data):
        cls.step_size = collector_cfg_data["collectorParams"]["stepSize"]
        cls.cfg_data = collector_cfg_data
        cls.end_time = params["endTime"] if 'endTime' in params else None
        cls.start_time = params["startTime"]
        cls.instance_id = collector_cfg_data["collectorParams"]["runningInstanceId"]["Instance_Id"]
        cls.params = params
        

    @classmethod
    def make_entry_RD(self, filename, entry_list):
        # create .tx file
        if entry_list:
            rd_file_path = self.cfg_data["collectorParams"]["acfRDfilePath"]
            tx_file_path = os.path.join(rd_file_path, filename)
            with open(tx_file_path, 'w') as file_rd:
                # add header       
                writer = csv.writer(file_rd)
                header = copy.deepcopy(self.tx_header)
                header.extend(entry_list)
                writer.writerows(header)

    @classmethod
    def _take_checksum(cls, file_path):
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum
    
    @classmethod
    def _write_checksum(cls, checksum):
        cls.cfg_data["collectorParams"]["checksum"] = checksum
        with open(cls.cfg_path, "w") as jsonFile:
            json.dump(cls.cfg_data, jsonFile, indent=4)  

class bulkPastcollection(Collection):
    name = "BULK PAST to PAST with date {} to {}"
    
    @classmethod    
    def collect(cls, params, collector_cfg_data):
        super().collect(params, collector_cfg_data)
        rfdataframe_json_path = cls.config_creation(collector_cfg_data)
        cls.invoke_rfDataframe(rfdataframe_json_path)
        print(f"Dataframe generated for {cls.start_time} to {cls.end_time}")
        cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])      
        return False      
 
class bulkpasttoFuturecollection(Collection):
    name = "BULK PAST to FUTURE"
    
    def collect(cls, params, collector_cfg_data):
        super().collect(params, collector_cfg_data)
        cls.wait_endtime_elapsed(params)
        rfdataframe_json_path = cls.config_creation(collector_cfg_data)
        cls.invoke_rfDataframe(rfdataframe_json_path)
        print(f"Dataframe generated for {cls.start_time} to {cls.end_time}")
        cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
        return False

    @classmethod
    def wait_endtime_elapsed(cls, params):
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True)
        if ("collection_stop_date" in params) and (params["collection_stop_date"] <= cls.end_time):
            cls.end_time = params["collection_stop_date"]
        print(f"Sleeping for {(cls.end_time - current_time)} until {cls.end_time}")
        time.sleep((cls.end_time - current_time).seconds)
        
class splitPastcollection(Collection):
    name = "Split PAST to PAST"
    
    # @classmethod
    # def is_reload(cls, cfg_path):        
    #     if cls.cfg_data["collectorParams"]["reloadCfg"] == "on":
    #         if not cls._take_checksum(cfg_path) == cls.cfg_data["collectorParams"]["checksum"]:
    #             print("----- Reloading rfDfCollector -----")
    #             cls._write_checksum(cls._take_checksum(cfg_path))
    #             return True
    #     return False

   
    @classmethod
    def collect(cls, params, collector_cfg_data):
        super().collect(params, collector_cfg_data)
        # return cls.is_reload("abc")                
        is_first_iter = True; break_flag=False
        while True:
            time.sleep(2)
            is_first_iter, break_flag = cls.get_collection_params(params, is_first_iter, break_flag)    
            # if cls.is_reload(params["cfg_path"]): return True
            rfdataframe_json_path = cls.config_creation(collector_cfg_data)  
            cls.invoke_rfDataframe(rfdataframe_json_path)
            print(f"Dataframe generated for {cls.start_time} to {cls.end_time}")
            cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
            if break_flag:
                break 
        return False, None

    @classmethod
    def get_collection_params(cls, params, is_first_iter, break_flag):
        cls.start_time = params["startTime"] if is_first_iter else cls.end_time
        cls.end_time = cls._calculate_datetime(cls.step_size[-2:], cls.step_size[:-2], cls.start_time)
        # cls.wait_endtime_elapsed()            
        if params["endTime"] <= cls.end_time:
            cls.end_time = cls.end_time - (cls.end_time - params["endTime"])
            break_flag=True
        return False, break_flag
                    
class splitpastFuturecollection(Collection):    
    name = "Split PAST to FUTURE"
    
    # @classmethod
    # def is_reload(cls, checksum, cfg_path):        
    #     if cls.cfg_data["collectorParams"]["reloadCfg"] == "on":
    #         if not cls._take_checksum(cfg_path) == checksum:
    #             print("----- Reloading rfDfCollector -----")
    #             return True, checksum
    #     return False

    @classmethod
    def _take_checksum(cls, file_path):
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum
   
    def collect(cls, params, collector_cfg_data):
        super().collect(params, collector_cfg_data)
        is_first_iter = True; break_flag=False
        while True:
            is_first_iter, break_flag = cls.get_collection_params(params, is_first_iter, break_flag)    
            cls.wait_endtime_elapsed()
            # if cls.is_reload(checksum, params["cfg_path"]): return True
            rfdataframe_json_path = cls.config_creation(collector_cfg_data)  
            cls.invoke_rfDataframe(rfdataframe_json_path)
            print(f"Dataframe generated for {cls.start_time} to {cls.end_time}")
            cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
            if break_flag:
                break
        return False, None

    @classmethod
    def get_duration(cls, params, is_first_iter):
        startTime = params["startTime"] if is_first_iter else cls.end_time        
        endTime = cls._calculate_datetime(cls.step_size[-2:], cls.step_size[:-2], startTime)        
        return startTime, endTime

    @classmethod
    def get_collection_params(cls, params, is_first_iter, break_flag):
        cls.start_time, cls.end_time = cls.get_duration(params, is_first_iter)
        stop_time = params["collection_stop_date"] if ("collection_stop_date" in params) and (params["collection_stop_date"] <= cls.end_time) else None
        if stop_time and stop_time <= params["endTime"]:
            cls.end_time = stop_time
            break_flag=True
        elif params["endTime"] <= cls.end_time:
            cls.end_time = cls.end_time - (cls.end_time - params["endTime"])
            break_flag=True
        return False, break_flag
    
    @classmethod
    def wait_endtime_elapsed(cls):
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True)
        if current_time <= cls.end_time:
            print("Waiting for", (cls.end_time - current_time))
            time.sleep((cls.end_time - current_time).seconds)
    
class foreverCollection(Collection):
    name = "Split forever Collection"

    # @classmethod
    # def is_reload(cls, checksum, cfg_path):        
    #     if cls.cfg_data["collectorParams"]["reloadCfg"] == "on":
    #         if not cls._take_checksum(cfg_path) == checksum:
    #             print("----- Reloading rfDfCollector -----")
    #             return True
    #     return False
    
    @classmethod
    def _take_checksum(cls, file_path):
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum    

    
    def collect(cls, params, collector_cfg_data):
        super().collect(params, collector_cfg_data)
        is_first_iter = True; break_flag=False
        while True:            
            is_first_iter, break_flag = cls.get_collection_params(params, is_first_iter, break_flag)    
            cls.wait_endtime_elapsed()
            # if cls.is_reload(checksum, params["cfg_path"]): return True
            rfdataframe_json_path = cls.config_creation(collector_cfg_data)  
            cls.invoke_rfDataframe(rfdataframe_json_path)
            print(f"Dataframe generated for {cls.start_time} to {cls.end_time}")
            cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
            if break_flag:
                break
        return False

    @classmethod
    def get_duration(cls, params, is_first_iter):
        startTime = params["startTime"] if is_first_iter else cls.end_time        
        endTime = cls._calculate_datetime(cls.step_size[-2:], cls.step_size[:-2], startTime)        
        return startTime, endTime

    @classmethod
    def get_collection_params(cls, params, is_first_iter, break_flag):
        cls.start_time, cls.end_time = cls.get_duration(params, is_first_iter)
        if ("collection_stop_date" in params) and (params["collection_stop_date"] <= cls.end_time):
            cls.end_time = params["collection_stop_date"]
            break_flag=True
        return False, break_flag
    
    @classmethod
    def wait_endtime_elapsed(cls):
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True)
        if current_time <= cls.end_time:
            print("Waiting for", (cls.end_time - current_time))
            time.sleep((cls.end_time - current_time).seconds)


if __name__ == "__main__":
    fp = FactoryProducer()
    collection, params, collector_cfg_data = fp.load()
    out = eval(collection)().collect(params, collector_cfg_data)
