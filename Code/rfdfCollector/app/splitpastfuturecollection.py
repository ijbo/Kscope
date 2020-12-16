import hashlib
import pytz
import time
from datetime import datetime
from collection import Collection
import logging
logger = logging.getLogger("rfdfCollector")


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
        """
        Takes the checkpoint of the configuration file.
        """
        checksum = hashlib.md5(open(file_path, "rb").read()).hexdigest()
        return checksum

    def collect(cls, params, collector_cfg_data):
        """
        Collects the dataframe on the basis of start and end time.
        """
        super().collect(params, collector_cfg_data)
        is_first_iter = True
        break_flag = False
        logger.info(f"Operation Type:Split, step_size:{cls.step_size}", extra=cls.log_format_dict())
        logger.info(f"Collection data:PAST TO FUTURE", extra=cls.log_format_dict())
        while True:
            is_first_iter, break_flag = cls.get_collection_params(params, is_first_iter, break_flag)    
            cls.wait_endtime_elapsed()
            # if cls.is_reload(checksum, params["cfg_path"]): return True
            rfdataframe_json_path = cls.config_creation(collector_cfg_data)
            cls.invoke_rfDataframe(rfdataframe_json_path)
            logger.info(f"Dataframe successfully generated for {cls.start_time} to {cls.end_time}", extra=cls.log_format_dict())
            cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
            logger.info(f"collected dataframe path:{collector_cfg_data['collectorParams']['rfdftempPath']}", extra=cls.log_format_dict())
            if break_flag:
                break
        return False, None

    @classmethod
    def get_duration(cls, params, is_first_iter):
        """
        Calculates end time on the basis of step size.
        """
        startTime = params["startTime"] if is_first_iter else cls.end_time
        endTime = cls._calculate_datetime(cls.step_size[-2:], cls.step_size[:-2], startTime)
        return startTime, endTime

    @classmethod
    def get_collection_params(cls, params, is_first_iter, break_flag):
        """
        Assigns the start and stop time.
        """
        cls.start_time, cls.end_time = cls.get_duration(params, is_first_iter)
        stop_time = params["collection_stop_date"] if ("collection_stop_date" in params) and (params["collection_stop_date"] <= cls.end_time) else None
        if stop_time and stop_time <= params["endTime"]:
            logger.info(f"Stop at time {stop_time} because collection time {cls.cfg_data['collectorParams']['collectionTime']} given", extra=cls.log_format_dict())
            cls.end_time = stop_time
            break_flag=True
        elif params["endTime"] <= cls.end_time:
            cls.end_time = cls.end_time - (cls.end_time - params["endTime"])
            break_flag=True
        return False, break_flag

    @classmethod
    def wait_endtime_elapsed(cls):
        dctimezone = pytz.timezone(cls.cfg_data["collectorParams"]["dctimezone"])
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True).astimezone(dctimezone).replace(tzinfo=None)
        if current_time <= cls.end_time:
            logger.info(f"Waiting for {(cls.end_time - current_time)} time elapsed", extra=cls.log_format_dict())
            time.sleep((cls.end_time - current_time).seconds)
