from datetime import datetime
import json
import os
from factory import Factory
import logging
logger = logging.getLogger("rfdfCollector")


class SplitCollectionFactory(Factory):

    def get_inputs(cls, arguments):
        """
        Defining instance ID , Collection time and Time step.
        """
        return super().get_inputs(arguments)

    def get_config_file(cls, arguments):
        """
        Read and validates configuration file then returns schedule parameters and configuration data.
        """
        params, collector_cfg_data = super().get_config_file(arguments)
        if ("mode" in collector_cfg_data["collectorParams"]) and (collector_cfg_data["collectorParams"]["mode"].lower() == 'inc'):
            path = cls.is_history_available(cls.instance_id)
            if path:
                startTime = cls.read_history_start_time(path)
                collector_cfg_data["job"]["executionMode"]["startTime"] = startTime
                logger.info(f"StartTime Updated : {startTime}", extra=cls.log_format_dict())
        return params, collector_cfg_data

    @classmethod
    def is_future_date(cls, end_time):
        """
        Checks end time with current time.
        :return: True if end time is greater then current time.
        """
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True)
        if end_time > current_time:
            return True
  
    @classmethod
    def is_history_available(cls,instance_id):
        path = f"{os.getcwd()}/incstate/{instance_id}_config_history.json"
        return path if os.path.exists(path) else None    
  
    @classmethod
    def read_history_start_time(cls, path):
        try:
            with open(path, "r") as jsonFile:
                data = json.load(jsonFile)
                return data["job"]["executionMode"]["endTime"]
        except Exception as ex:
            logger.error(f"Unable to read endTime from history config file: {ex}", extra=cls.log_format_dict())


    @classmethod
    def get_collection(cls, params, collector_cfg_data):
        """
        Validates start and end time and returns configuration file data and parameters(start and end time).
        """
        if 'endTime' in params:
            if cls.is_future_date(params["endTime"]):
                return "splitpastfuturecollection.splitpastFuturecollection", params, collector_cfg_data
            else:
                return "splitpastcollection.splitPastcollection", params, collector_cfg_data
        else:
            return "forevercollection.foreverCollection", params, collector_cfg_data
