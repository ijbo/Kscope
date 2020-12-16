from datetime import datetime
from factory import Factory
import logging
logger = logging.getLogger("rfdfCollector")

class BulkCollectionFactory(Factory):

    def get_inputs(cls, arguments):
        """
        Defining instance ID , Collection time and Time step.
        """
        return super().get_inputs(arguments)

    def get_config_file(cls, arguments):
        """
        Read and validates configuration file then returns schedule parameters and configuration data.
        """
        return super().get_config_file(arguments)

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
    def get_collection(cls, params, collector_cfg_data):
        """
        Validates start and end time and returns configuration file data and parameters(start and end time).
        """
        if cls.is_future_date(params["endTime"]):
            
            return "bulkpasttofuturecollection.bulkpasttoFuturecollection", params, collector_cfg_data
        else:
            return "bulkpastcollection.bulkPastcollection", params, collector_cfg_data
