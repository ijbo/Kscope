import multiprocessing as mp
from parseSubscription import Subscription
import asyncio
import os
import threading
import numpy as np
import requests
import shutil
from services import Service
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

def getMetadata(idrac, port, file_collection_path, file_collection_time):
    meta_dict = {}
    response = requests.get(f"https://{user}:{passwd}@{idrac}/redfish/v1/", verify=False)
    json_response = response.json()
    service_data = Service(**json_response)
    serviceMeta = service_data.getMetadata()
    filename = getFileDescriptor(serviceMeta, idrac)
    try:
        fd = open(f"{file_collection_path}/output/{filename}", "a+")
    except FileNotFoundError as ex:
        if not os.path.exists(f"{file_collection_path}"):
            os.makedirs(file_collection_path)    
        fd = open(f"{file_collection_path}/output/{filename}", "a+")
    # meta_dict[idrac] = getFile
    return [serviceMeta[0], serviceMeta[1], fd, file_collection_path, file_collection_time ]
   

def replaceMembers(members):
    return [eval(str(x).replace('@', '').replace('.', '_'))  for x in members]

def deleteSubscription(subscription_to_delete, idrac):
    if subscription_to_delete:
        # print("Subscription is deleted")
        response = requests.delete(f"https://{user}:{passwd}@{idrac}{subscription_to_delete[0]}", verify=False)
        if response.status_code == 200:
            print("Subscription is deleted")
        else:
            print(response.status_code)
            print(response.json())
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

    response = requests.post(source_url, data=json.dumps(request_body),headers=headers, verify=False)
    if response.status_code == 201:
        print("Subscription Successfully")
        return 200
    else:
        print(response.json())
        return 400

def checkPort(ip_list, total_subscription, idrac_port, idrac):
    ip_list = [(ip, port, odata_id) for ip, port,odata_id in ip_list if ip == SOURCE_IP]
    delete_subsciption_ids = [] 
    if ip_list:
        for ip in ip_list:
            if ip[1] == idrac_port:
                print("IP adress and port is already subscribed")
                delete_subsciption_ids.clear()
                return delete_subsciption_ids, 0, idrac
            else:
                delete_subsciption_ids.append(ip[2])
        return delete_subsciption_ids, 2, idrac
    else:
        return delete_subsciption_ids, 1, idrac

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
   
def getSubscription(idracs_IPs: [], idrac_port, q):
    user = "root"
    passwd = "calvin"

    for idrac in idracs_IPs:
        response = requests.get(f"https://{user}:{passwd}@{idrac}/redfish/v1/EventService/Subscriptions/", verify=False)
        json_response = response.json()
        json_response["Members"] = replaceMembers(json_response["Members"])
        
        # print(json_response)
        subscription_data = Subscription(**json_response)
        
        def getDetailsubscription(idrac):
            members_ip = []
            if subscription_data.Members:
                for member in subscription_data.Members:
                    response_detail = requests.get(f"https://{user}:{passwd}@{idrac}{member.odata_id}", verify=False)
                    response = response_detail.json()
                    members_ip.append((response["Destination"], member.odata_id))
                    # print(smember.odata_id)
            else:
                pass    
                # No members available.
                # postSubscription()
            if len(members_ip) >= 1:
                return checkPort(fetchIP(members_ip), len(members_ip), idrac_port, idrac)
           
            else:
                return [], 3, idrac
                        
    return getDetailsubscription(idrac)

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

def createJsonFile(ipaddr, idrac):
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = ipaddr[0] + '_' + ipaddr[1] + '_' + idrac + '_' + getTimestamp() +".jsonl"
    # filename = getFileDescriptor(serviceMeta, idrac)
    try:
        fd = open(f"{ipaddr[3]}/output/{filename}", "a+")
    except FileNotFoundError as ex:
        if not os.path.exists(f"{file_collection_path}"):
            os.makedirs(file_collection_path)    
        fd = open(f"{ipaddr[3]}/output/{filename}", "a+")
    return fd

def canGernerateNewJsonFile(ts, collection_time):
    previousDate = datetime.strptime(ts,"%Y%m%d%H%M%S")
    newDate = datetime.now().replace(microsecond=False)
    duration = (newDate - previousDate)
    sec = duration.seconds
    if sec >= int(collection_time):
        return newDate
    return False

def processData(newsocketconn, fromaddr, context, ipaddr):
    if useSSL:
        connstreamout = context.wrap_socket(newsocketconn, server_side=True)
    else:
        connstreamout = newsocketconn
    global event_count, data_buffer
    outdata = headers = HostDetails = ""
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
                        shutil.move(f"{ipaddr[3]}/output/{filename}", f"{ipaddr[3]}/complete/{filename}")
                        fd.close()
                        
                        filename = ipaddr[0] + '_' + ipaddr[1] + '_' + fromaddr[0] + '_' + new_time +".jsonl"
                        try: fd = open(f"{ipaddr[3]}/output/{filename}", "a+")
                        except FileNotFoundError as ex:
                            if not os.path.exists(f"{file_collection_path}"):
                                os.makedirs(file_collection_path)
                        ipaddr[2] = open(f"{ipaddr[3]}/output/{filename}", "a+")
                    fd.write(bodydata)
                    fd.write("\n")
                except Exception as ex:
                    print("Exception Occured =", ex)    
                
                StatusCode = """HTTP/1.1 200 OK\r\n\r\n"""
                connstreamout.send(bytes(StatusCode, 'UTF-8'))
                # try:
                #    if event_count.get(str(fromaddr[0])):
                #        event_count[str(fromaddr[0])] = event_count[str(fromaddr[0])] + 1
                #    else:
                #        event_count[str(fromaddr[0])] = 1
                #    # logger.info("Event Counter for Host %s = %s" % (str(fromaddr[0]), event_count[fromaddr[0]]))
                # except Exception as err:
                #    print(traceback.print_exc())
                # for th in threads:
                #     th.join()   

            if p.method() == 'GET':
                
                res = "HTTP/1.1 200 OK\n" \
                      "Content-Type: application/json\n" \
                      "\n" + json.dumps(data_buffer)
                connstreamout.send(res.encode())
                data_buffer.clear()

        except Exception as err:
            outdata = connstreamout.read()
            traceback.print_exc()
            print("Data needs to read in normal Text format.")
            print(outdata)

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
        bindsocket.listen(5)
    except Exception as e:
        print(f"Unable to start listener on port {listenerport}")
        sys.exit(0)
    
    print('Listening on {}:{}'.format(listenerip, listenerport))
    event_count = {}
    data_buffer = []
    counter = 1
    while True:
        threads =[]
        # 
        try:
            newsocketconn, fromaddr = bindsocket.accept()
            if fromaddr[0] in mappingDict.keys():
                ipaddr_obj = mappingDict[fromaddr[0]]
                try:
                    ### Multiple Threads to handle different request from different servers
                    # print(f"{counter} Event get at timestamp {datetime.now()}")
                    # asyncio.create_task(processData(newsocketconn, fromaddr, context, ipaddr_obj))
                    # processData(newsocketconn, fromaddr, context, ipaddr_obj)
                    #print("I didn't wait for processData")
                    threading.Thread(target=processData, args=(newsocketconn, fromaddr,context, ipaddr_obj)).start()
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
        mappingDict[idrac] = getMetadata(idrac, batch['port'], batch["file_collection_path"], batch["file_collection_time"])
        # mappingDict[idrac] = getMetadata(idrac, batch['port'])
        # {"idrac_A": ('service_tag', 'mac_addr', 'file_descriptor_A') }
    # delete_subscription_ids, flag, idrac = getSubscription(batch["iDRACS"], batch['port'], q)

    # if flag == 3:
    #     makeSubscription(batch['port'], idrac)
    # elif flag in [1,2]:
    #    deleteSubscription(delete_subscription_ids, idrac)
    #    makeSubscription(batch['port'], idrac)
    # else:
    #    pass
    time.sleep(5)
    print(f"{batch['port']} going to subscribe")
    # asyncio.run(binder(batch['port'], mappingDict))
    binder(batch['port'], mappingDict)
    # print(delete_subscription_ids, flag, idrac)
    # if delete_subscription_ids and flag == 2:
    #     deleteSubscription(delete_subscription_ids, idrac)
    #     rc = makeSubscription(batch['port'], idrac)
    #     if rc == 200:
    #         binder(batch['port'])
    # if delete_subscription_ids and flag == 1:
    #     rc = makeSubscription(batch['port'], idrac)
    #     if rc == 200:
    #         binder(batch['port'])
    print(p_name, "<-----Exits") 

