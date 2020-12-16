import os
import json
import datetime
import argparse
import logging
import logging.config
from bulkcollectionfactory import BulkCollectionFactory
from splitcollectionfactory import SplitCollectionFactory
from customLogHandlers import CustomFileHandler
# import logging
# logger = logging.getLogger("rfdfCollector")


class FactoryProducer:

    def get_arguments(self):
        """
        Assign input parameters from shell script to the arguments.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--c", dest="collection_time", help="Provide Colection time duration")
        parser.add_argument("-s", "--s", dest="steps", help="Provide interval on which you want to run rfDatafamr")
        parser.add_argument("-r", "--r", dest="rfdf_configpath", help="Provide instance name")
        parser.add_argument("-i", "--i", dest="instance_id", help="Provide instance name")
        args = parser.parse_args()
        return args

    def get_factory(self):
        """
        On the basis of steps returns the factory class(SplitCollectionFactory or BulkCollectionFactory) and arguments.
        """
        args = self.get_arguments()
        if args.steps:
            return SplitCollectionFactory, args
        else:
            return BulkCollectionFactory, args
    
    def set_logger(self, args, uniqueid):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        log_file_name= f"logs/rfdfcollector_{args.instance_id}_{uniqueid}_{timestamp}.log"
        path = args.rfdf_configpath
        with open(path, "r") as jsonFile:
            data = json.load(jsonFile)
   
        logging.config.dictConfig(data["logging"])
        root = logging.getLogger("rfdfCollector")                
        root.setLevel(logging.DEBUG)
        handler = CustomFileHandler(os.path.abspath(log_file_name), maxBytes=2000000)
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | Id:%(instance_id)s | uniqueid:%(uid)s | %(funcName)s():%(lineno)s | PID:%(process)d | %(message)s', "%Y%m%d%H%M%S")
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        root.addHandler(handler)
                        

    def load(self):
        """
        Validates start and end time and returns configuration file data and parameters(start and end time).
        """
        fac, arguments = self.get_factory()        
        unique_id = fac().get_inputs(arguments)
        self.set_logger(arguments, unique_id)
        params, collector_cfg_data = fac().get_config_file(arguments)
        if ("endTime" in params) and ("startTime" in params) and (params["endTime"] <= params["startTime"]):
            # Logger
            print("Please check start time and end tine. It seems start time is larger then end time. ")
            os.kill(os.getpid(), 9)
        return fac().get_collection(params, collector_cfg_data)
