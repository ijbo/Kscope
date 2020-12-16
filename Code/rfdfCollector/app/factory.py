import re
import pytz
import os
import hashlib
import json
import psutil
import setproctitle as spt
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
logger = logging.getLogger("rfdfCollector")

class Factory(ABC):
    base_config_path = None
    base_data_path  = None
    cfg_path = None
    cfg_data = None
    instance_id = None
    collection_time = None
    steps = None

    @classmethod
    @abstractmethod
    def get_inputs(cls, arguments):
        """
        Defining instance ID , Collection time and Time step.
        """
        cls.cfg_path = arguments.rfdf_configpath
        cls.instance_id = arguments.instance_id
        cls.collection_time = arguments.collection_time
        cls.steps = arguments.steps
        cls.uniqueid = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True).strftime("%Y%m%d%H%M%S")
        return cls.uniqueid

    @classmethod
    @abstractmethod
    def get_config_file(cls, arguments):
        """
        Read and validates configuration file then returns schedule parameters and configuration data.
        """
        cls.read_cfgfile(arguments)
        cls.validation()
        return cls.get_schedule_params(), cls.cfg_data
    
    @classmethod
    def log_format_dict(cls):
        return {"instance_id":cls.instance_id, "uid":cls.uniqueid}

    @classmethod
    def _calculate_datetime(cls, unit, value, date_time):
        """
        Calculates datetime based on one of the following:
            - Minutes
            - Hours
            - Days
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
    def _get_datetime(cls, date_time, format, replace=False):
        """
        Reformat datetime in standard form by resetting microsecond to 0.
        """
        if replace:
            return datetime.strptime(str(date_time.replace(microsecond=0)), format)
        return datetime.strptime(str(date_time), format)

    @classmethod
    def get_stop_time(cls):
        """
        Calculates termination time.
        """
        return cls._calculate_datetime(cls.collection_time[-2:],
                                       cls.collection_time[:-2],
                                       cls._get_datetime(datetime.now(),
                                                        "%Y-%m-%d %H:%M:%S",
                                                        replace=True
                                                        )
                                       )
    @classmethod
    def convert_timezone(cls, dt, time_caption):
        """

        """
        try:
            if  "dctimezone" in cls.cfg_data["collectorParams"]:
                dctimezone = pytz.timezone(cls.cfg_data["collectorParams"]["dctimezone"])
                new_dt = cls._get_datetime(dt, "%Y-%m-%d %H:%M:%S").astimezone(dctimezone)
                logger.info(f'{time_caption} are converted in the timezone: {cls.cfg_data["collectorParams"]["dctimezone"]}', extra=cls.log_format_dict())
                return str(datetime.strptime(str(new_dt.replace(microsecond=0, tzinfo=None)), "%Y-%m-%d %H:%M:%S"))
            return dt
        except Exception as ex:
            logger.exception(ex, extra=cls.log_format_dict())
            return dt

    @classmethod
    def get_schedule_params(cls):
        """
        Defining the start and termination time.
        """
        _params = {}
        end_time = cls.cfg_data['job']['executionMode']["endTime"]
        start_time = cls.cfg_data['job']['executionMode']["startTime"]
        if end_time: _params["endTime"] = cls._get_datetime(cls.convert_timezone(end_time, "End Time"), "%Y-%m-%d %H:%M:%S")
        if start_time: _params["startTime"] = cls._get_datetime(cls.convert_timezone(start_time, "Start Time"), "%Y-%m-%d %H:%M:%S")
        if cls.collection_time: _params["collection_stop_date"] = cls.get_stop_time()
        _params["cfg_path"] = cls.cfg_path
        _params["uniqueid"] = cls.uniqueid
        return _params

    @classmethod
    def read_cfgfile(cls, arguments):
        """
        Load configuration file to set the parameters.

        Kills the process if configuration file not found.
        """
        if not cls.cfg_path:
            logger.info("Please Select config File with -r operation", extra=cls.log_format_dict())
            os.kill(os.getpid(), 9)
        else:
            with open(cls.cfg_path, "r") as jsonFile:
                data = json.load(jsonFile)
            cls.cfg_data = data
            logger.info(f"rfdfCollector_config_path:{cls.cfg_path}", extra=cls.log_format_dict())
            logger.info(f"startTime:{cls.cfg_data['job']['executionMode']['startTime']}", extra=cls.log_format_dict())
            logger.info(f"endTime:{cls.cfg_data['job']['executionMode']['endTime']}", extra=cls.log_format_dict())
            logger.info(f"collection_time:{cls.collection_time}", extra=cls.log_format_dict())
            logger.info(f"Step_Size:{cls.steps}", extra=cls.log_format_dict())


    @classmethod
    def set_process_name(cls, process_name):
        """
        Assign process name to the process ID.
       :param process_name: In upper case
        :return: Process name
        """
        pid = os.getpid()
        spt.setproctitle(process_name)
        logger.info(f"Process Name:{process_name}", extra=cls.log_format_dict())

    @staticmethod
    def check_process_running(process_name):
        """
        Checks the if the process is running or not.
        :return: True if the process is running else False.
        """
        for proc in psutil.process_iter():
            try:
                if process_name.lower() == proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    @classmethod
    def _take_checksum(cls, file_path):
        """
        Takes the checkpoint of the configuration file.
        """
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum

    @classmethod
    def write_checksum(cls):
        """
        Write the checkpoint of the configuration file.
        """
        checksum = cls._take_checksum(cls.cfg_path)
        cls.cfg_data["collectorParams"]["checksum"] = checksum
        logger.info(f"New Checksum added in config:{checksum}", extra=cls.log_format_dict())

    @classmethod
    def validation(cls):
        """
        Validates the instance ID and updates configuration file.
        """
        __instances_list = cls.cfg_data["collectorParams"]["instanceId"]
        if cls.instance_id:
            cls._is_available_instance(__instances_list)
            if not cls.check_process_running("rfDfCollector -InstanceId " + cls.instance_id.upper()):
                cls.set_process_name("rfDfCollector -InstanceId " + cls.instance_id.upper())
                cls.write_checksum()
                cls.update_cfg()
            else:
                logger.error(f"Process is already running with instance {cls.instance_id}", extra=cls.log_format_dict())
                os.kill(os.getpid(), 9)
        else:
            logger.error(f"Please provide Instance Id", extra=cls.log_format_dict())
            os.kill(os.getpid(), 9)

    @classmethod
    def _is_available_instance(cls, instance_list):
        """
        Checks the availability of instance.
        :return: True if instance Id is present.
        """
        if list(filter(lambda x: x.lower() == cls.instance_id.lower(), instance_list)):
            return True
        else:
            logger.error(f"Please select Instance Id among the {instance_list}", extra=cls.log_format_dict())
            os.kill(os.getpid(), 9)

    @classmethod
    def __update_cfg_data(cls, key, value):
        """
        Updates configuration file by adding parameters.
        """
        cls.cfg_data["collectorParams"][key] = value
        logger.info(f"config updated with {key}:{value}", extra=cls.log_format_dict())

    @classmethod
    def __make_directories(cls, paths, type_dir="data"):
        """
        Create directories for configuration file.
        """
        base_path = cls.base_config_path if type_dir == "config" else cls.base_data_path
        try:
            os.makedirs(os.path.join(base_path, *paths))
        except Exception as ex:
            logger.exception(f"Exception Occurs :{ex} ", extra=cls.log_format_dict())
            
        return os.path.join(base_path, *paths)
   
    @classmethod
    def get_mounted_path(cls, paths):
        base_path = "/home/web/calsoft/data"
        try:
            return os.path.join(base_path, *paths)
        except Exception as ex:
            logger.exception(f"Exception Occurs:{ex} ", extra=cls.log_format_dict())


    @classmethod
    def update_paths(cls):
        """
        Updates path to configuration file.
        """
        custom_config_path = cls.__make_directories([cls.instance_id, str(os.getpid()), cls.uniqueid], type_dir="config")
        data_temp_path = cls.__make_directories([cls.instance_id, str(os.getpid()), str(cls.uniqueid), "temp"])
        host_temp_path = cls.get_mounted_path([cls.instance_id, str(os.getpid()), str(cls.uniqueid), "temp"])
        cls.__update_cfg_data("customConfig", custom_config_path)
        cls.__update_cfg_data("rfdftempPath", data_temp_path)
        cls.__update_cfg_data("hosttempPath", host_temp_path)

    @classmethod
    def write_to_cfg(cls):
        """
        Dumps configuration file into .json format.
        """
        with open(cls.cfg_path, "w") as jsonFile:
            json.dump(cls.cfg_data, jsonFile, indent=4)

    @classmethod
    def set_output_folder(cls):
        """
        Assign output folder path.
        """
        outputdir = cls.cfg_data["job"]["outputFolder"]
        dataframe_temp_path = cls.cfg_data["collectorParams"]["rfdftempPath"]
        cls.cfg_data["job"]["outputFolder"] = os.path.join(outputdir,
                                               re.sub(r'\/temp\/?',"", re.sub(r'^(\/[^\/]+)*\/data\/?',"", dataframe_temp_path)))

    @classmethod
    def update_cfg(cls):
        """
        Updates configuration file.
        """
        __collector_params = cls.cfg_data["collectorParams"]
        cls.__update_cfg_data("collectionTime", cls.collection_time)
        cls.__update_cfg_data("stepSize", cls.steps)
        cls.__update_cfg_data("runningInstanceId", {"Instance_Id": cls.instance_id,
                                                    "Process_Id": os.getpid()})

        cls.base_config_path = cls.cfg_data["collectorParams"]["baseConfigPath"]
        cls.base_data_path = cls.cfg_data["collectorParams"]["baseDataPath"]

        cls.update_paths()
        cls.write_to_cfg()
        cls.set_output_folder()

