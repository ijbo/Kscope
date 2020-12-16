from collection import Collection
import time
import logging
logger = logging.getLogger("rfdfCollector")



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
        """
        Collects the dataframe on the basis of start and end time.
        """
        super().collect(params, collector_cfg_data)
        # return cls.is_reload("abc")                
        is_first_iter = True; break_flag=False
        logger.info(f"Operation Type:Split, step_size:{cls.step_size}", extra=cls.log_format_dict())
        logger.info(f"Collection data:PAST TO PAST", extra=cls.log_format_dict())
        while True:
            time.sleep(2)
            is_first_iter, break_flag = cls.get_collection_params(params, is_first_iter, break_flag)    
            # if cls.is_reload(params["cfg_path"]): return True
            rfdataframe_json_path = cls.config_creation(collector_cfg_data)  
            cls.invoke_rfDataframe(rfdataframe_json_path)
            logger.info(f"Dataframe successfully generated for {cls.start_time} to {cls.end_time}", extra=cls.log_format_dict())
            cls.move_files(collector_cfg_data["collectorParams"]["rfdftempPath"])
            logger.info(f"collected dataframe path:{collector_cfg_data['collectorParams']['rfdftempPath']}", extra=cls.log_format_dict())
            if break_flag:
                break 
        return False, None

    @classmethod
    def get_collection_params(cls, params, is_first_iter, break_flag):
        """
        Calculates end time on the basis of step size.
        """
        cls.start_time = params["startTime"] if is_first_iter else cls.end_time
        cls.end_time = cls._calculate_datetime(cls.step_size[-2:], cls.step_size[:-2], cls.start_time)
        # cls.wait_endtime_elapsed()            
        if params["endTime"] <= cls.end_time:
            cls.end_time = cls.end_time - (cls.end_time - params["endTime"])
            break_flag=True
        return False, break_flag
