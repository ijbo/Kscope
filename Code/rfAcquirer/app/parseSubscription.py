from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ValidationError, validator

class Member(BaseModel):
    odata_id: str


class Subscription(BaseModel):
    Description: str
    Members: List[Member] = []
    Name: str
    SubscriptionMembers: List[str] = []

    # @validator('*')
    # def check_empty(cls, x):
    #     if not x:
    #         raise ValueError("Please provide all fields")
    #     return x

    def SubscriptionMembers(cls):
        print(cls)

    

class DetailSubscription(BaseModel):
    Context: str
    Desciption: str
    Destination: str
    EventFormatType: str
    Id: str
    Name: str
    Protocol: str
    SubscriptionType: str


