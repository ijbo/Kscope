import os, signal
import hashlib
import glob
import time
import json
import random
import psutil
import shutil
import argparse
import setproctitle as spt
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
logger = logging.getLogger("acf")



class Factory(ABC):
    base_config_path = "../rfDataframe/config"
    base_data_path  = "../rfDataframe/data"
    cfg_path = None
    cfg_data = None
    instance_id = None
    collection_time = None
    steps = None

    @classmethod
    @abstractmethod
    def get_inputs(cls, arguments):
        cls.cfg_path = arguments.rfdf_configpath
        cls.instance_id = arguments.instance_id
        cls.collection_time = arguments.collection_time
        cls.steps = arguments.steps

    @classmethod
    @abstractmethod
    def get_config_file(cls, arguments):
        cls.read_cfgfile(arguments)
        cls.validation()
        return cls.get_schedule_params(), cls.cfg_data


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
    def _get_datetime(cls, date_time, format, replace=False):
        if replace:
            return datetime.strptime(str(date_time.replace(microsecond=0)), format)
        return datetime.strptime(str(date_time), format)

    @classmethod
    def get_stop_time(cls):
        return cls._calculate_datetime( cls.collection_time[-2:],
                                        cls.collection_time[:-2],
                                        cls._get_datetime(datetime.now(),
                                                            "%Y-%m-%d %H:%M:%S",
                                                            replace=True
                                                        )
                                        )
    @classmethod
    def get_schedule_params(cls):
        logger.info("Connecting to Params")
        _params = {}
        end_time = cls.cfg_data['job']['executionMode']["endTime"]
        start_time = cls.cfg_data['job']['executionMode']["startTime"]
        if end_time:_params["endTime"] = cls._get_datetime(end_time, "%Y-%m-%d %H:%M:%S")
        if start_time:_params["startTime"] = cls._get_datetime(start_time, "%Y-%m-%d %H:%M:%S")
        if cls.collection_time:_params["collection_stop_date"] = cls.get_stop_time()
        _params["cfg_path"]=cls.cfg_path
        return _params

    @classmethod
    def read_cfgfile(cls, arguments):
        if not cls.cfg_path:
            # Logger
            print("Please Select config File with -r operation")
            os.kill(os.getpid(), 9)
        else:
            with open(cls.cfg_path, "r") as jsonFile:
                data = json.load(jsonFile)
            cls.cfg_data = data

    @staticmethod
    def set_process_name(process_name):
        pid = os.getpid()
        print("My Process ID - ", pid)
        spt.setproctitle(process_name)

    @staticmethod
    def check_process_running(process_name):
        for proc in psutil.process_iter():
            try:
                if process_name.lower() == proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    @classmethod
    def _take_checksum(cls, file_path):
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum

    @classmethod
    def write_checksum(cls):
        checksum = cls._take_checksum(cls.cfg_path)
        cls.cfg_data["collectorParams"]["checksum"] = checksum

    @classmethod
    def validation(cls):
        __instances_list = cls.cfg_data["collectorParams"]["instanceId"]
        if cls.instance_id:
            cls._is_available_instance(__instances_list)
            if not cls.check_process_running(cls.instance_id.upper()):
                cls.set_process_name("rfDfCollector -InstanceId " + cls.instance_id.upper())
                cls.write_checksum()
                cls.update_cfg()
            else:
                print("Already Running with instance {} ".format(args.instance_id))
                os.kill(os.getpid(), 9)
        else:
            print("Please provide instance_id")
            os.kill(os.getpid(), 9)

    @classmethod
    def _is_available_instance(cls, instance_list):
        if list(filter(lambda x: x.lower() == cls.instance_id.lower(), instance_list)):
            return True
        else:
            print("Please select instance_id among the {}".format(instance_list))
            os.kill(os.getpid(), 9)

    @classmethod
    def __update_cfg_data(cls, key, value):
        cls.cfg_data["collectorParams"][key] = value

    @classmethod
    def __make_directories(cls, paths, type_dir="data"):
        base_path = cls.base_config_path if type_dir == "config" else cls.base_data_path
        try:
            os.makedirs(os.path.join(base_path, *paths))
        except Exception as ex:
            pass
        return os.path.join(base_path, *paths)

    @classmethod
    def update_paths(cls):
        custom_config_path = cls.__make_directories([cls.instance_id, str(os.getpid())], type_dir="config")
        data_temp_path = cls.__make_directories([cls.instance_id, str(os.getpid()), "temp"])
        cls.__update_cfg_data("customConfig", custom_config_path)
        cls.__update_cfg_data("rfdftempPath", data_temp_path)

    @classmethod
    def write_to_cfg(cls):
        with open(cls.cfg_path, "w") as jsonFile:
            json.dump(cls.cfg_data, jsonFile, indent=4)

    @classmethod
    def set_output_folder(cls):
        outputdir = cls.cfg_data["job"]["outputFolder"]
        cls.cfg_data["job"]["outputFolder"] = os.path.join(outputdir, cls.instance_id, str(os.getpid()))

    @classmethod
    def update_cfg(cls):
        __collector_params = cls.cfg_data["collectorParams"]
        cls.__update_cfg_data("collectionTime", cls.collection_time)
        cls.__update_cfg_data("stepSize", cls.steps)
        cls.__update_cfg_data("runningInstanceId", {"Instance_Id": cls.instance_id,
                                                    "Process_Id":os.getpid()})
        cls.update_paths()
        cls.write_to_cfg()
        cls.set_output_folder()


class BulkCollectionFactory(Factory):

    def get_inputs(cls, arguments):
        return super().get_inputs(arguments)

    def get_config_file(cls, arguments):
        return super().get_config_file(arguments)

    @classmethod
    def is_future_date(cls, end_time):
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True)
        if end_time > current_time:
            return True

    @classmethod
    def get_collection(cls, params, collector_cfg_data):
        print("In Bulk get Collection")
        if cls.is_future_date(params["endTime"]):
            return "bulkpasttoFuturecollection", params, collector_cfg_data
        else:
            return "bulkPastcollection", params, collector_cfg_data

class SplitCollectionFactory(Factory):

    def get_inputs(cls, arguments):
        return super().get_inputs(arguments)

    def get_config_file(cls, arguments):
        return super().get_config_file(arguments)

    @classmethod
    def is_future_date(cls, end_time):
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True)
        if end_time > current_time:
            return True

    @classmethod
    def get_collection(cls, params, collector_cfg_data):
        print("In Split get Collection")

        if 'endTime' in params:
            if cls.is_future_date(params["endTime"]):
                print("Future")
                return "splitpastFuturecollection", params, collector_cfg_data
            else:
                return "splitPastcollection", params, collector_cfg_data
        else:
            return "foreverCollection", params, collector_cfg_data

class FactoryProducer:

    def get_arguments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--c", dest ="collection_time", help="Provide Colection time duration")
        parser.add_argument("-s", "--s", dest ="steps", help="Provide interval on which you want to run rfDatafamr")
        parser.add_argument("-r", "--r", dest="rfdf_configpath", help="Provide instance name")
        parser.add_argument("-i", "--i", dest="instance_id", help="Provide instance name")
        args = parser.parse_args()
        return args

    def get_factory(self):
        args = self.get_arguments()
        if args.steps:
            return SplitCollectionFactory, args
        else:
            return BulkCollectionFactory, args

    def set_logger(self, args):
        path = args.rfdf_configpath
        with open(path, "r") as jsonFile:
            data = json.load(jsonFile)
        logging.config.dictConfig(data["logging"])
        root = logging.getLogger("acf")

    def load(self):
        fac, arguments = self.get_factory()
        fac().get_inputs(arguments)
        params, collector_cfg_data =  fac().get_config_file(arguments)
        self.set_logger(arguments)
        if("endTime" in params) and ("startTime" in params) and (params["endTime"] <= params["startTime"]):
            # Logger
            os.kill(os.getpid(), 9)
        return fac().get_collection(params, collector_cfg_data)

