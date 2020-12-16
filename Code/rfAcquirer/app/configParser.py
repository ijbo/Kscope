from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ValidationError, validator


class AcquirerConfig(BaseModel):
    batch_size: int
    file_collection_time: str
    iDRACS: List[str] = [] 
    ports_list: List[int] = []
    file_collection_path: str
    log_file_path: str
    log_file_size: str

    @validator('*')
    def check_empty(cls, x):
        if not x:
            raise ValueError("Please provide all fields")
        return x



