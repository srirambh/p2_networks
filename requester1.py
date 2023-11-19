import argparse 
import socket
import struct
import csv
from datetime import datetime
from datetime import timedelta
from collections import defaultdict
import collections
import os 

MAX_BYTES = 6000

 
def makeRequestPacket(filename,window):
    byteString =bytes(filename,'utf-8')
    return struct.pack(f"!cII{len(byteString)}s",b'R',0,window,byteString)

def sendRequest(destHostname,destPort, srcPort, filename,window, emulatorName, emulatorPort):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    payload = makeRequestPacket(filename,window)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encapsulate(1,ownIP,srcPort,socket.inet_aton(socket.gethostbyname(destHostname)),destPort,payload)
    sock.sendto(packet, (emulatorName, emulatorPort))
    
def makeAckPacket(sequenceNum):
    return struct.pack(f"!cII",b'A',sequenceNum,0)

def sendAck(destIP,destPort,srcPort,emulatorName,emulatorPort, sequenceNum):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    payload = makeAckPacket(sequenceNum)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encapsulate(1,ownIP,srcPort,destIP,destPort,payload)
    sock.sendto(packet, (emulatorName, emulatorPort))

def encapsulate(priority, src_ip, src_port, dest_ip, dest_port,payload):
    packet = struct.pack(f"!B4sH4sHI{len(payload)}s",priority,src_ip,src_port,dest_ip,dest_port,len(payload),payload)
    return packet

def decapsulate(packet):
    header = struct.unpack_from("!B4sH4sHI",packet)
    length = header[5]
    payload = struct.unpack_from(f"!{length}s",packet,offset=17)[0]
    return header,payload


def printEnd(address, sequence):
    print("END Packet")
    print("send time: ",datetime.utcnow())
    print("requester addr: ",address)
    print("Sequence num: ",sequence)
    #print("length: ",0)
    #print("payload: ")
    print("")

def receivePackets(sock,emulatorName,emulatorPort,ownPort,numSenders, receivedMessages= defaultdict(lambda : {})):
    end = 0
    totalLengths = defaultdict(lambda : 0)
    totalPackets = defaultdict(lambda : 0)
    startTime = datetime.utcnow()
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))

    #[(sourceAdd,sourcePort)][SeqNo][Text]
    while end!=numSenders:
        data, addr = sock.recvfrom(MAX_BYTES)
        outerHeader, payload = decapsulate(data)
        if(outerHeader[3]!=ownIP):
            continue
        header = struct.unpack_from("!cII",payload)
        length = header[2]
        totalLengths[(outerHeader[1],outerHeader[2])] += length
        totalPackets[(outerHeader[1],outerHeader[2])]+= 1 if header[0]!=b'E' else 0
        if header[0]==b'E':
            end +=1
            endTime = datetime.utcnow()
            printEnd(socket.inet_ntoa(outerHeader[1]),header[1])
            milliseconds = (endTime-startTime)/timedelta(milliseconds=1)
            print("-------SUMMARY-------")
            print("Sender addr: ",socket.inet_ntoa(outerHeader[1]))
            print("Total Data packets: ", totalPackets[(outerHeader[1],outerHeader[2])])
            print("Total Data bytes: ", totalLengths[(outerHeader[1],outerHeader[2])])
            print("Average packets/second: ", totalPackets[(outerHeader[1],outerHeader[2])]*1000/milliseconds)
            print("Duration: ", milliseconds, " ms")
            print("--------------------\n")
        else:
            received = struct.unpack_from(f"!{length}s",payload,offset=9)[0].decode('utf-8')

            receivedMessages[(outerHeader[1],outerHeader[2])][header[1]] = received
            sendAck(outerHeader[1],outerHeader[2],ownPort,emulatorName,emulatorPort,header[1])

    return receivedMessages


def parseTracker():
    with open("tracker.txt", "r") as f:
        d = defaultdict(lambda : [])
        reader = csv.reader(f,delimiter=' ')
        for row in reader:
            d[row[0]].append((int(row[1]), row[2], int(row[3])))
        
    for key in d.keys():
        d[key] = sorted(d[key], key =lambda x: x[0])
    return d



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port")
    parser.add_argument("-o", "--fileoption")
    parser.add_argument("-f", "--f_hostname")
    parser.add_argument("-e", "--f_port")
    parser.add_argument("-w", "--window")
    args = parser.parse_args()
    d = parseTracker()
    window = int(args.window)
    f_port = int(args.f_port)
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    sock.bind((socket.gethostname(), int(args.port)))
    with open(args.fileoption, "w+") as f:
        pass
    numSenders = len(d[args.fileoption])
    for i in d[args.fileoption]:
        id = i[0]

        #hostname, port, 
        sendRequest(i[1],i[2],int(args.port),args.fileoption,window,args.f_hostname,f_port)


    senderTexts = receivePackets(sock,args.f_hostname,f_port,int(args.port),numSenders)
    for i in d[args.fileoption]:
        senderIP = socket.inet_aton(socket.gethostbyname(i[1]))
        senderPort = i[2]
        for key,fragment in collections.OrderedDict(sorted(senderTexts[senderIP, senderPort].items())).items():
            #fragment is (seqno, text)
            with open(args.fileoption, "a") as f:
                f.write(fragment)

