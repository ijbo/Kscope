import multiprocessing as mp
from parseSubscription import Subscription
import requests
import ssl
from http_parser.http import HttpStream
from http_parser.reader import SocketReader
import traceback
import asyncio
from websockets.extensions import permessage_deflate
import re
import socket
import json
import websockets
import sys
import time


# def replaceStr(str, response_dict):
#     if type(response_dict) == "dict":
#         for key in response_dict.keys():
#             if type(response_dict[key]) is list:
#                 for k,v in response_dict.items():
#                     print(k, v)
#                     replaceStr(str,k)
#             else:
#                 if '@' in response_dict[key]:
#                     response_dict[key].replace('@', '')
#     print(response_dict)
SOURCE_IP = "192.168.1.109"
# SOURCE_PORT = '8028'
user = "root"
passwd="calvin"
useSSL = True

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

def checkPort(ip_list, total_subscription, idrac_port):
    ip_list = [(ip, port, odata_id) for ip, port,odata_id in ip_list if ip == SOURCE_IP]
    delete_subsciption_ids = [] 
    if ip_list:
        for ip in ip_list:
            if ip[1] == idrac_port:
                print("IP adress and port is already subscribed")
                delete_subsciption_ids.clear()
                return delete_subsciption_ids, 0
            else:
                print(ip)
                delete_subsciption_ids.append(ip[2])
        return delete_subsciption_ids, 2
    else:
        return delete_subsciption_ids, 1



def fetchIP(ip_list):
    reg_str = "\/\/(.*?)\/"
    total_ips = len(ip_list)
    identical_subscriptions = []
    for ip in ip_list:
        ipa = re.findall(reg_str, ip[0])
        if ipa:
            identical_subscriptions.append((ipa[0].split(':')[0], ipa[0].split(':')[1], ip[1])) 
    print(identical_subscriptions, "<--ide")
    return identical_subscriptions

def reportSubscription():
    pass
   
def getSubscription(idracs_IPs: [], idrac_port, q):
    print("IN get_subscription", idracs_IPs)
    user = "root"
    passwd = "calvin"

    for idrac in idracs_IPs:
        response = requests.get(f"https://{user}:{passwd}@{idrac}/redfish/v1/EventService/Subscriptions/", verify=False)
        json_response = response.json()
        json_response["Members"] = replaceMembers(json_response["Members"])
        
        print(json_response)
        subscription_data = Subscription(**json_response)
        
        def getDetailsubscription():
            members_ip = []
            if subscription_data.Members:
                for member in subscription_data.Members:
                    print(f"https://{user}:{passwd}@{idrac}{member.odata_id}")
                    response_detail = requests.get(f"https://{user}:{passwd}@{idrac}{member.odata_id}", verify=False)
                    response = response_detail.json()
                    # print(response["Destination"], "<------ Destination")
                    members_ip.append((response["Destination"], member.odata_id))
                    # print(smember.odata_id)
            else:
                pass    
                # No members available.
                # postSubscription()
            print(members_ip, "IP")
            delete_subscription_ids, flag = checkPort(fetchIP(members_ip), len(members_ip), idrac_port,)
            return delete_subscription_ids, flag, idrac
                        
    return getDetailsubscription()


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

def processData(newsocketconn, fromaddr, context):
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
                for eachHeader in headers.items():
                    if eachHeader[0] == 'Host' or eachHeader[0] == 'host':
                        HostDetails = eachHeader[1]

                ### Read the json response and print the output
                print("Server IP Address is ", fromaddr[0])
                outdata = dict()
                # current_date = DT.now().strftime("%Y%m%d")
                # folder_suffix = "-{}".format(listenerport)  if listenerport != '443' else ''
                # directory = '{}{}/{}/{}'.format(report_location,folder_suffix,fromaddr[0],current_date)
                try:
                    print(bodydata)
                    with open("output.json", "a+") as f:
                        f.write(bodydata)
                        f.write("\n")
                except json.decoder.JSONDecodeError:
                    print("Exception occurred while processing report")

                # influx_thread = threading.Thread(target=writeReportToInflux, args=(fromaddr[0],directory, outdata))
                # threads.append(influx_thread)
                # influx_thread.start()

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


async def handler(websocket, path):
    # print(websocket)        
    async for row in websocket:
        try:
            print(row)
            # print(row.decode())
        except Exception as ex:
            print(ex)
            pass    

async def start(listenerip):
        print("STARTS WEBSOCKET", listenerip)
        try:
            return await websockets.serve(handler,listenerip, 8029, ping_interval=None, max_size=None,
                                    max_queue=None, close_timeout=None, extensions=[
                    permessage_deflate.ServerPerMessageDeflateFactory(
                        server_max_window_bits=11,
                        client_max_window_bits=11,
                        compress_settings={'memLevel': 4},
                    ),
                ])
        except Exception as ex:
            print(ex)

def start_sender(listenerip):
    asyncio.get_event_loop().run_until_complete(start(listenerip))
    asyncio.get_event_loop().run_forever()


def binder(listenerport):
    useSSL = True
    if useSSL:
        print(ssl.Purpose.CLIENT_AUTH)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile="cert.pem", keyfile="server.key")
        print(context)
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
    while True:
        # threads =[]
        print("Listening.")
        try:
            newsocketconn, fromaddr = bindsocket.accept()
            print("---->",newsocketconn, fromaddr)
            try:
                pass
                ### Multiple Threads to handle different request from different servers
                processData(newsocketconn, fromaddr, context)
                # threading.Thread(target=processData, args=(newsocketconn, fromaddr, threads)).start() Thread-001--[request]
            except Exception as err:
                print(err)
        except Exception as err:
            print("Exception occurred in socket binding.")
            print(err)


# async def echo(websocket, path):
#     async for message in websocket:
#         await websocket.send(message)

# asyncio.get_event_loop().run_until_complete(
#     websockets.serve(echo, 'localhost', 8765))
# asyncio.get_event_loop().run_forever()

def runListener(batch, q):
    p_name = mp.current_process().name
    print(p_name, "<------Starts")
    time.sleep(1)
    # listenerip = getIp()
    binder(batch['port'])
    #start_sender(listenerip)
    # delete_subscription_ids, flag, idrac = getSubscription(batch["iDRACS"], batch['port'], q)
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
