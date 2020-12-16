import multiprocessing as mp
from parseSubscription import Subscription
import asyncio
import os
import gzip
import numpy as np
import requests
import shutil
from services import Service
from requests.packages import urllib3
import ssl
from datetime import datetime, timedelta
from http_parser.http import HttpStream
from http_parser.reader import SocketReader
import traceback
from websockets.extensions import permessage_deflate
import re
import socket
import json
import websockets
import sys
import time



SOURCE_IP = "192.168.12.228"
user = "root"
passwd="calvin"
useSSL = True


def background(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if callable(f):
            return loop.run_in_executor(None, f, *args, **kwargs)
        else:
            raise TypeError('Task must be a callable')    
    return wrapped


def getTimestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def getFileDescriptor(metadata, idrac):
    filename = metadata[0] + '_' + metadata[1]+ '_' + idrac + '_' + getTimestamp() +".jsonl"
    return filename

def apiGetCall(url, apiname, idrac):
    try:
        response = requests.get(url, verify=False, timeout=5)
        return response.status_code, response.json()
    except (urllib3.exceptions.MaxRetryError, requests.exceptions.ConnectTimeout) as err:
        return 408, f"Timeout error occurred while invoking {url} with iDRAC {idrac}"

def apiDeleteCall(url, apiname, idrac):
    try:
        response = requests.delete(url, verify=False, timeout=2)
        return response.status_code, response.json()
    except (urllib3.exceptions.MaxRetryError, requests.exceptions.ConnectTimeout) as err:
        return 408, f"Timeout error occurred while invoking {url} with iDRAC {idrac}"

def apiPostCall(url, apiname, idrac, requestDict, headers):
    try:
        response = requests.post(url, data=json.dumps(requestDict), headers=headers, verify=False)
        return response.status_code, response.json()
    except (urllib3.exceptions.MaxRetryError, requests.exceptions.ConnectTimeout,) as err:
        return 408, f"Timeout error occurred while invoking {url} with iDRAC {idrac}"


def fetchMetadata(idrac, port, file_collection_path, file_collection_time):
    meta_dict = {}
    url = f"https://{user}:{passwd}@{idrac}/redfish/v1/"
    response_code, json_response = apiGetCall(url, 'Root API', idrac)
    if response_code == 200:
        service_data = Service(**json_response)
        serviceMeta = service_data.getMetadata()
        filename = serviceMeta[0] + '_' + serviceMeta[1]+ '_' + idrac + '_' + getTimestamp() +".jsonl"
        try:
            fd = open(f"{file_collection_path}/output/{filename}", "a+")
        except FileNotFoundError as ex:
            if not os.path.exists(f"{file_collection_path}"):
                os.makedirs(file_collection_path)    
            fd = open(f"{file_collection_path}/output/{filename}", "a+")
        # meta_dict[idrac] = getFile
        return [serviceMeta[0], serviceMeta[1], fd, file_collection_path, file_collection_time]
    elif response_code == 408:
        print(json_response)
    else:
        print(f"{url} Failed with status code {response_code} and error Message {json_response}") 

def replaceMembers(members):
    return [eval(str(x).replace('@', '').replace('.', '_'))  for x in members]

def deleteSubscription(subscription_to_delete, idrac):
    if subscription_to_delete:
        # print("Subscription is deleted")
        url = f"https://{user}:{passwd}@{idrac}{subscription_to_delete}"
        response_code, json_response = apiDeleteCall(url, 'Delete Subscription', idrac)
        if response_code == 200:
            print(f"Subscription is successfully deleted for {idrac}")
        elif response_code == 408:
            print(json_response)
        else:
            print(f"{url} Failed with status code {response_code} and error Message {json_response}") 

    else:
        pass
    
def makeSubscription(idrac_port, idrac_ip):
    source_url = f"https://{user}:{passwd}@{idrac_ip}/redfish/v1/EventService/Subscriptions/"
    destination = f"https://{SOURCE_IP}:{idrac_port}/{idrac_ip}/443"
    request_body = dict()
    request_body["Context"] = "Public"
    request_body["Description"] = "Event Subscription Details"
    request_body["Destination"] = destination
    request_body["EventFormatType"] = "MetricReport"
    request_body["EventTypes"] = ["MetricReport"]
    request_body["Protocol"] = "Redfish"
    request_body["SubscriptionType"] = "RedfishEvent"
    headers = {'Content-type': 'application/json'}
    response_code, json_response  = apiPostCall(source_url, "Post subscription", idrac_ip, request_body, headers)
    
    if response_code == 201:
        print(f"Subscription sucessfully done for iDRAC {idrac_ip} on port {idrac_port}")
    elif response_code == 408:
        print(json_response)
    else:
        print(f"{source_url} Failed with status code {response_code} and error Message {json_response}") 


def checkPort(ip_list, total_subscription, idrac_port, idrac):
    ip_list = [(ip, port, odata_id) for ip, port,odata_id in ip_list]
    delete_subscription_ids = [] 
    if ip_list:
        for ip in ip_list:
            if ip == SOURCE_IP:
                if ip[1] == idrac_port:
                    delete_subscription_ids.clear()
                    return delete_subscription_ids, 0, idrac
                else:
                    # same Ip but different port
                    delete_subscription_ids.append(ip[2])
                    return delete_subscription_ids, 2, idrac
            else:
                delete_subscription_ids.append(ip[2])
                return delete_subscription_ids, 1, idrac

def fetchIP(ip_list):
    reg_str = "\/\/(.*?)\/"
    total_ips = len(ip_list)
    identical_subscriptions = []
    for ip in ip_list:
        ipa = re.findall(reg_str, ip[0])
        if ipa:
            identical_subscriptions.append((ipa[0].split(':')[0], ipa[0].split(':')[1], ip[1])) 
    return identical_subscriptions

def reportSubscription():
    pass
   
def getSubscription(idrac, idrac_port, q):
    user = "root"
    passwd = "calvin"
    url = f"https://{user}:{passwd}@{idrac}/redfish/v1/EventService/Subscriptions/"
    response_code, json_response = apiGetCall(url, 'Get Subscription', idrac)
    if response_code == 200:
        json_response["Members"] = replaceMembers(json_response["Members"])
    
        # print(json_response)
        subscription_data = Subscription(**json_response)
        def getDetailsubscription(idrac):
            members_ip = []
        
            if subscription_data.Members:
                for member in subscription_data.Members:
                    response_detail = requests.get(f"https://{user}:{passwd}@{idrac}{member.odata_id}", verify=False)
                    response = response_detail.json()
                    if response["SubscriptionType"] == "RedfishEvent":
                        members_ip.append((response["Destination"], member.odata_id))
                    # print(smember.odata_id)
            else:
                print("HERE")
                return None, 3, idrac    
        
            if len(members_ip) >= 1:
                print(fetchIP(members_ip))
                return checkPort(fetchIP(members_ip), len(members_ip), idrac_port, idrac)
            
                
        return getDetailsubscription(idrac)

    elif response_code == 408:
        print(json_response)
        return None, None, None
    else:
        print(f"{url} Failed with status code {response_code} and error Message {json_response}")
        return None, None, None

def getIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception as e:
        print(e, "Exception")
        IP = '127.0.0.1'
    finally:
        print("Close")
        s.close()
    return IP


def getTimestampfromFilename(fd):
    # print(dir(fd))
    file_ts = fd.name.split('_')[3].split(".")[0]
    return file_ts

@background
def processData(newsocketconn, fromaddr, context, ipaddr):
    if useSSL:
        connstreamout = context.wrap_socket(newsocketconn, server_side=True)
    else:
        connstreamout = newsocketconn
    try:
        try:
            ### Read the json response using Socket Reader and split header and body
            r = SocketReader(connstreamout)
            p = HttpStream(r)
            headers = p.headers()

            if p.method() == 'POST':
                bodydata = p.body_file().read()
                bodydata = bodydata.decode("utf-8", errors='ignore')

                ### Read the json response and print the output
                # outdata = dict()
                try :
                    old_time = getTimestampfromFilename(ipaddr[2])
                    new_time = (datetime.strptime(old_time,"%Y%m%d%H%M%S") + timedelta(seconds=int(ipaddr[4]))).strftime("%Y%m%d%H%M%S")
                    cur_time =  datetime.now().strftime("%Y%m%d%H%M%S")
                    a = np.where(int(cur_time) > int(new_time),new_time,False)
                    fd = ipaddr[2]
                    if eval(a.item(0)):
                        filename = fd.name.split("/")[-1]
                        # print(filename, "<--test")
                        
                        os.system(f"gzip {ipaddr[3]}/output/{filename}")
                        shutil.move(f"{ipaddr[3]}/output/{filename}.gz", f"{ipaddr[3]}/complete/")
                        
                        fd.close()
                        
                        filename = ipaddr[0] + '_' + ipaddr[1] + '_' + fromaddr[0] + '_' + new_time +".jsonl"
                        try: fd =open(f"{ipaddr[3]}/output/{filename}", "a+")
                        except FileNotFoundError as ex:
                            if not os.path.exists(f"{file_collection_path}"):
                                os.makedirs(file_collection_path)
                        ipaddr[2] = open(f"{ipaddr[3]}/output/{filename}", "a+")
                    # print(bodydata, type(bodydata), "<---bodydata")
                    fd.write(bodydata)
                    fd.write("\n")
                
                except Exception as ex:
                    print("Exception Occured =", ex)    
                
                StatusCode = """HTTP/1.1 200 OK\r\n\r\n"""
                connstreamout.send(bytes(StatusCode, 'UTF-8'))
               
            # if p.method() == 'GET':
                
            #     res = "HTTP/1.1 200 OK\n" \
            #           "Content-Type: application/json\n" \
            #           "\n" + json.dumps(data_buffer)
            #     connstreamout.send(res.encode())
            #     data_buffer.clear()

        except Exception as err:
            outdata = connstreamout.read()
            traceback.print_exc()
            print("Data needs to read in normal Text format.")

    finally:
        connstreamout.shutdown(socket.SHUT_RDWR)
        connstreamout.close()


def binder(listenerport, mappingDict):
    useSSL = True
    if useSSL:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile="app/cert.pem", keyfile="app/server.key")
    listenerip = getIp()
    try:
        bindsocket = socket.socket()
        bindsocket.bind((listenerip, int(listenerport)))
        bindsocket.listen(128)
        print(listenerip)
    except Exception as e:
        print(f"Unable to start listener on port {listenerport}")
        sys.exit(0)
    
    print('Listening on {}:{}'.format(listenerip, listenerport))
    while True:
        try:
            newsocketconn, fromaddr = bindsocket.accept()
            print(newsocketconn, fromaddr)
            if fromaddr[0] in mappingDict.keys():
                ipaddr_obj = mappingDict[fromaddr[0]]
                try:
                    ### Multiple Threads to handle different request from different servers
                    # print(f"{counter} Event get at timestamp {datetime.now()}")
                    # asyncio.create_task(processData(newsocketconn, fromaddr, context, ipaddr_obj))
                    processData(newsocketconn, fromaddr, context, ipaddr_obj)
                    # ipaddr_obj[2].close()
                    print("I didn't wait for processData")
                    # threading.Thread(target=processData, args=(newsocketconn, fromaddr,context, ipaddr_obj, threads)).start()
                    # counter = counter + 1
                except Exception as err:
                    print(err)
            else:
                pass
                # put in the Queue
        except Exception as err:
            print("Exception occurred in socket binding.")
            print(err)



def runListener(batch, q):
    p_name = mp.current_process().name
    print(p_name, "<------Starts")
    time.sleep(1)
    # GET SUBSCRIPTION and DETAIL SUBSCRIPTION
    mappingDict = {}
    for idrac in batch['iDRACS']:
        metadata_list = fetchMetadata(idrac, batch['port'], batch["file_collection_path"], batch["file_collection_time"])
        if metadata_list:
            mappingDict[idrac] = metadata_list
        
        members, flag, idrac  = getSubscription(idrac, batch['port'], q)
        print(members, flag, idrac, "HH")
        if not flag:
            # idrac get subscription apiendpoint is not callable
            pass
        elif flag == 0:
            # already subscribed
            print(f"Given ip {members[0]} is already subscribed with port {batch['port']} to the iDRAC {batch['iDRACS']}")
        elif flag in [1, 2]:
            # 1-Different destination ip, 2-Same Ip but different port
            deleteSubscription(members[0], idrac )
            makeSubscription(batch['port'], idrac)
        elif flag == 3:
            # When No member are subscribed 
            makeSubscription(batch['port'], idrac)
            
    binder(batch['port'], mappingDict)
    print(p_name, "<-----Exits") 

