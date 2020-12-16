from collection import Collection
import logging
logger = logging.getLogger("rfdfCollector")


class bulkPastcollection(Collection):
    name = "BULK PAST to PAST with date {} to {}"

    @classmethod
    def collect(cls, params, collector_cfg_data):
        """
        Collects the dataframe on the basis of start and end time.
        """
        super().collect(params, collector_cfg_data)
        logger.info(f"Operation Type:BULK", extra=cls.log_format_dict())
        logger.info(f"Collection data:PAST TO PAST", extra=cls.log_format_dict())              
        rfdataframe_json_path = cls.config_creation(collector_cfg_data)
        cls.invoke_rfDataframe(rfdataframe_json_path)
        logger.info(f"Dataframe successfully generated for {cls.start_time} to {cls.end_time}", extra=cls.log_format_dict())
        cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
        logger.info(f"collected dataframe path:{collector_cfg_data['collectorParams']['rfdftempPath']}", extra=cls.log_format_dict())
        return False
