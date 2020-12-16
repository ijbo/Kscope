from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, ValidationError, validator, Field


class Dell(BaseModel):
    ServiceTag = str
    ManagerMACAddress = str

class Service(BaseModel):
    Description: str
    Name: str
    # Oem: Dict['str', Dell]
    Oem: dict

    def getMetadata(cls):
        return [cls.Oem["Dell"]["ServiceTag"], cls.Oem["Dell"]["ManagerMACAddress"].replace(":", "")]

