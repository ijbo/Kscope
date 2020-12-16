import re
import os
import pytz
import hashlib
import glob
import copy
import time
import socket
import uuid
import csv
import json
import random
import shutil
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import subprocess
from subprocess import Popen, PIPE
import logging
logger = logging.getLogger("rfdfCollector")

class Collection(ABC):
    dataframe_path = None
    metadata_path = None
    step_size = None
    params = None
    cfg_data = None
    tx_header = [["sys_creation_date", "sys_update_date", "File_name", "Source_host", "Target_host", "Source_file_path", "Target_file_Path", "file_tx_type","target_username","target_pass"]]
    base_data_path  = None
    archieve_path = None
    hostname = None

    # base_data_path  = "/home/web/calsoft/data":

    @classmethod
    @abstractmethod
    def collect(cls, params, collector_cfg_data):
        """
        Set parameters and path for the datafram and metadata.
        """
        cls.setter(params, collector_cfg_data)
        cls.set_directories(collector_cfg_data)
        if collector_cfg_data["collectorParams"]["recoveryMode"].lower() == 'on':
            cls.recover()
   
    @classmethod
    def log_format_dict(cls):
        return {"instance_id":cls.instance_id, "uid":cls.uniqueid}

    @classmethod
    def config_creation(cls, cfg_data, steps=None):
        """
        Invoke the creation of the folder where dataframe will be stored.
        :return: Path to the folder.
        """
        cfg_data["job"]["executionMode"]["endTime"] = str(cls.end_time)
        cfg_data["job"]["executionMode"]["startTime"] = str(cls.start_time)
        rfdataframe_json_path = cls.create_rfdataframe_config(cfg_data)
        logger.info(f"rfDataframe config Path:{rfdataframe_json_path}", extra=cls.log_format_dict())
        return rfdataframe_json_path

    @classmethod
    def create_tx_df_entry(cls, dataframe_name):
        """
        Create transaction for dataframe.
        """
        return [str(datetime.now()), str(datetime.now()), dataframe_name,
                "192.168.8.109", cls.cfg_data["archiveStorage"]["targetHost"] , os.path.join(cls.cfg_data["collectorParams"]["rfdftempPath"], dataframe_name),
                os.path.join(cls.archieve_path, cls.hostname, str(datetime.now().year), str(datetime.now().month), str(datetime.now().day), "dataframes", dataframe_name), cls.cfg_data["archiveStorage"]["fileOperation"], "czope", "rlaQYZQeqL8rqQSn"]

    @classmethod
    def create_tx_metadata_entry(cls, metadata_name):
        """
        Create transaction for metadata.
        """
        return [str(datetime.now()), str(datetime.now()), metadata_name,
                "192.168.8.109", cls.cfg_data["archiveStorage"]["targetHost"], os.path.join(cls.cfg_data["collectorParams"]["rfdftempPath"], metadata_name),
                os.path.join(cls.archieve_path,cls.hostname, str(datetime.now().year), str(datetime.now().month), str(datetime.now().day),  "metadata", metadata_name), cls.cfg_data["archiveStorage"]["fileOperation"],"czope", "rlaQYZQeqL8rqQSn"]
  

    @classmethod
    def create_tx_log_entry(cls, log_name):
        """
        Create transaction for metadata.
        """
        return [str(datetime.now()), str(datetime.now()), log_name,
        "192.168.8.109", cls.cfg_data["archiveStorage"]["targetHost"], os.path.join(cls.cfg_data["collectorParams"]["rfdftempPath"], log_name), os.path.join(cls.archieve_path, cls.hostname, str(datetime.now().year), str(datetime.now().month), str(datetime.now().day) ,"LClogs", log_name), cls.cfg_data["archiveStorage"]["fileOperation"], "czope", "rlaQYZQeqL8rqQSn"]

 
    @classmethod
    def move_files(cls, destination):
        """
        Move files to selected destination path.
        """
        entries = []
        df_files = glob.glob(f"{cls.dataframe_path}/*")
        for f in df_files:
            logger.info(f, extra=cls.log_format_dict())
            logger.info(destination, extra=cls.log_format_dict())
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_df_entry(f.rsplit("/")[-1]))
        log_files = glob.glob(f"{cls.lclog_path}/*")
        for f in log_files:
            logger.info(f, extra=cls.log_format_dict())
            logger.info(destination, extra=cls.log_format_dict())
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_log_entry(f.rsplit("/")[-1]))
        meta_files = glob.glob(f"{cls.metadata_path}/*")
        for f in meta_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_metadata_entry(f.rsplit("/")[-1]))
        cls.make_entry_RD("dataframes_{}.tx".format(str(uuid.uuid4())), entries)

    @classmethod
    def convert_timezone(cls, dt):
        """

        """
        try:
            if "dctimezone" in cls.cfg_data["collectorParams"]:
                dctimezone = pytz.timezone(cls.cfg_data["collectorParams"]["dctimezone"])
                new_dt = cls._get_datetime(dt, "%Y-%m-%d %H:%M:%S").astimezone(dctimezone)
                return str(datetime.strptime(str(new_dt.replace(microsecond=0, tzinfo=None)), "%Y-%m-%d %H:%M:%S"))
            return dt
        except Exception as ex:
            return dt

    @classmethod
    def find_error_log(cls, logs_message):
        exp = r'.* - error:.*'
        for log in logs_message.splitlines():
            is_error = re.match(exp, log)
            if is_error:
                return True
        return False


    @classmethod
    def invoke_rfDataframe(cls, config_name):
        """
        Invoke rfDataframe docker container.
        """
        try:
            cmd = f"docker exec -it {cls.Rfdf_Container} node rfDataframe --rfdf-config {config_name}".split()
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            out, err = p.communicate()
            if out:
                logger.info(out.decode(), extra=cls.log_format_dict())
                # if cls.find_error_log(out.decode()):
                #    exit()
                p = subprocess.Popen(["free", "-h"], stdout=subprocess.PIPE)
                avail, err = p.communicate()
                logger.info(avail.decode(), extra=cls.log_format_dict())
            else:
                exit()
        except Exception as ex:
            logger.error(f"Error Occured while invoking rfDataframe {ex}", extra=cls.log_format_dict())
            exit()

    @classmethod
    def recover_move_files(cls, dataframe_path, metadata_path, lclog_path, destination):
        """
        
        """
        entries = []
        df_files = glob.glob(f"{dataframe_path}/*")
        for f in df_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_df_entry(f))
        log_files = glob.glob(f"{lclog_path}/*")
        for f in log_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_log_entry(f))
        meta_files = glob.glob(f"{metadata_path}/*")
        for f in meta_files:
            shutil.move(f, os.path.join(destination, f.rsplit("/")[-1]))
            entries.append(cls.create_tx_metadata_entry(f))
        cls.make_entry_RD("dataframes_{}.tx".format(str(uuid.uuid4())), entries)

    @classmethod
    def recover(cls):
        """

        """
        logger.info("Recovering old dataframes", extra=cls.log_format_dict())
        path = f"{cls.base_data_path}/{cls.instance_id}"
        process_ids = os.listdir(path)
        for process_id in process_ids:
            dataframe_path = f"{path}/{process_id}/dataframes" 
            metadata_path  =  f"{path}/{process_id}/metadata"
            lclog_path = f"{path}/{process_id}/LClogs"
            destination  =  f"{path}/{process_id}/temp"
            cls.recover_move_files(dataframe_path, metadata_path, lclog_path, destination)

    @classmethod
    def _make_directories(cls, base_path, folder_name):
        """
        Make directory at the given path.
        """
        try:
            os.makedirs(os.path.join(base_path, folder_name))
        except Exception as ex:
            logger.error(ex, exc_info=True, extra=cls.log_format_dict())            
        return os.path.join(base_path, folder_name)

    @classmethod
    def _make_rfdataframe_config(cls, cfg_data):
        """
        Creates a dictionary of  ['job', 'database', 'redfish'] from configuration data.
        :return: dictionary
        """
        _config_json = {}
        for key in ['job', 'database', 'redfish', 'lcLogMeasurements']:
            _config_json[key] = cfg_data[key]
        return _config_json

    @classmethod
    def write_json(cls, cfg_data, config_name, config_json):
        """
        Dumps custom configuration file into .json format.
        """
        config_path = cfg_data["collectorParams"]["customConfig"]
        try:
            with open(os.path.join(config_path, config_name), "w") as jsonFile:
                json.dump(config_json, jsonFile, indent=4)
        except Exception as ex:
            logger.exception("rfDataframe dataframes and metadata folders are not created.", extra=cls.log_format_dict())

    @classmethod
    def create_rfdataframe_config(cls, cfg_data):
        """
         Assigns the name of the data frame randomly.
        :return: Path where the dataframe will be stored.
        """
        _name_pattern = "config_{}.json"
        _config_json = cls._make_rfdataframe_config(cfg_data)
        _config_name = _name_pattern.format(random.randint(1, 100000))
        cls.write_json(cfg_data, _config_name, _config_json)
        return os.path.join(re.sub(r'^(\/[^\/]+)*\/config\/?', "config/", cfg_data["collectorParams"]["customConfig"]),
                             _config_name)

    @classmethod
    def _calculate_datetime(cls, unit, value, date_time):
        """
        Calculates datetime based on one of the following:
            - Minutes
            -Hours
            -Days
        Pass if not mentioned any of the  above units.
        """
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
        """
        Reformat datetime in standard form by resetting microsecond to 0.
        """
        if replace:
            return datetime.strptime(str(date_time.replace(microsecond=0)), format)    
        return datetime.strptime(str(date_time), format)

    @classmethod
    def set_directories(cls, collector_cfg_data):
        """
        Assigns the path for dataframe and metadata output files.
        """
        dataframes_base_path = "/".join(collector_cfg_data["collectorParams"]["rfdftempPath"].rsplit("/")[:-1])
        cls.dataframe_path = cls._make_directories(dataframes_base_path, 'dataframes')
        cls.metadata_path = cls._make_directories(dataframes_base_path, 'metadata')
        cls.lclog_path = cls._make_directories(dataframes_base_path, 'LClogs')
        logger.info(cls.dataframe_path, extra=cls.log_format_dict())
        cls._make_directories(dataframes_base_path, 'tmp')

    @classmethod
    def setter(cls, params, collector_cfg_data):
        """
        Assigns the parameters from configuration file to class variable [step_size, start_time, end_time, instance_id, cfg_data].
        """
        cls.step_size = collector_cfg_data["collectorParams"]["stepSize"]
        cls.cfg_data = collector_cfg_data
        cls.end_time = params["endTime"] if 'endTime' in params else None
        cls.start_time = params["startTime"]
        cls.instance_id = collector_cfg_data["collectorParams"]["runningInstanceId"]["Instance_Id"]
        cls.uniqueid = params["uniqueid"]
        cls.base_data_path = collector_cfg_data["collectorParams"]["baseDataPath"]
        cls.archieve_path = collector_cfg_data["archiveStorage"]["targetFilepath"]
        cls.params = params
        cls.Rfdf_Container = collector_cfg_data["rfdataframeDetails"]["Rfdf_Container"]        
        cls.hostname = os.environ.get("hostname")

    @classmethod
    def make_entry_RD(self, filename, entry_list):
        """
        Append data entries into csv file.
        """
        # create .tx file
        if entry_list:
            rd_file_path = self.cfg_data["collectorParams"]["acfRDfilePath"]
            tx_file_path = os.path.join(rd_file_path, filename)
            with open(tx_file_path, 'w+') as file_rd:
                # add header       
                writer = csv.writer(file_rd)
                header = copy.deepcopy(self.tx_header)
                header.extend(entry_list)
                writer.writerows(header)

    @classmethod
    def _take_checksum(cls, file_path):
        """
        Takes the checkpoint of the configuration file.
        """
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum

    @classmethod
    def _write_checksum(cls, checksum):
        """
        Write the checkpoint of the configuration file.
        """
        cls.cfg_data["collectorParams"]["checksum"] = checksum
        with open(cls.cfg_path, "w") as jsonFile:
            json.dump(cls.cfg_data, jsonFile, indent=4)  

if __name__ == "__main__":
    try:
        from factoryproducer import FactoryProducer
        fp = FactoryProducer()
        collection, params, collector_cfg_data = fp.load()
        import bulkpasttofuturecollection, bulkpastcollection
        import splitpastcollection, splitpastfuturecollection, forevercollection
        out = eval(collection)().collect(params, collector_cfg_data)
    except Exception as ex:
        logger.error(f"Exception Occurs - {ex}", exc_info=True, extra=cls.log_format_dict())
        exit()
