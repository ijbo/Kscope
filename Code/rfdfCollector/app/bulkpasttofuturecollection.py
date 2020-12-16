import time
from datetime import datetime
from collection import Collection
import logging
logger = logging.getLogger("rfdfCollector")


class bulkpasttoFuturecollection(Collection):
    name = "BULK PAST to FUTURE"

    def collect(cls, params, collector_cfg_data):
        """
        Collects the dataframe on the basis of start and end time.
        """
        super().collect(params, collector_cfg_data)
        logger.info(f"Operation Type:BULK",extra=cls.log_format_dict())
        logger.info(f"Collection data:PAST TO FUTURE", extra=cls.log_format_dict())
        cls.wait_endtime_elapsed(params)
        rfdataframe_json_path = cls.config_creation(collector_cfg_data)
        cls.invoke_rfDataframe(rfdataframe_json_path)
        logger.info(f"Dataframe successfully generated for {cls.start_time} to {cls.end_time}", extra=cls.log_format_dict())
        cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
        logger.info(f"collected dataframe path:{collector_cfg_data['collectorParams']['rfdftempPath']}", extra=cls.log_format_dict())
        return False

    @classmethod
    def wait_endtime_elapsed(cls, params):
        """
        Delays the process till end time is reached.
        """
        dctimezone = pytz.timezone(cls.cfg_data["collectorParams"]["dctimezone"])
        current_time = cls._get_datetime(datetime.now(), "%Y-%m-%d %H:%M:%S", replace=True).astimezone(dctimezone)
        if ("collection_stop_date" in params) and (params["collection_stop_date"] <= cls.end_time):
            cls.end_time = params["collection_stop_date"]
        logger.info(f"Waiting for {(cls.end_time - current_time)} time elapsed", extra=cls.log_format_dict())
        time.sleep((cls.end_time - current_time).seconds)
