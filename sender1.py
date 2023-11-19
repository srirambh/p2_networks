import argparse
import socket
import struct
from datetime import datetime
from datetime import timedelta
import os
import time
import errno
from collections import defaultdict
MAX_BYTES = 6000
ACKS = defaultdict(lambda : False)

SUPRESSOUTPUT = True
 
def encapsulate(priority, src_ip, src_port, dest_ip, dest_port,payload):
    packet = struct.pack(f"!B4sH4sHI{len(payload)}s",priority,src_ip,src_port,dest_ip,dest_port,len(payload),payload)
    return packet


def decapsulate(packet):
    header = struct.unpack_from("!B4sH4sHI",packet)
    length = header[5]
    payload = struct.unpack_from(f"!{length}s",packet,offset=17)[0]
    return header,payload

def readFile(filename, b):
    bytearr = []
    with open(filename, "rb") as f:
        while (byte := f.read(b)):
            bytearr.append(byte)
    return bytearr


def receiveRequest(serversocket):
    data, addr = serversocket.recvfrom(MAX_BYTES)
    outHeader,payload = decapsulate(data)
    request = struct.unpack_from("!cII",payload)
    window = request[2]
    # fileName = struct.unpack_from(f"!{length}s",data,offset=9)[0].decode('utf-8')
    fileName = payload[9:].decode('utf-8')
    #print("file name recieved : "+fileName)
    return fileName, addr, window, outHeader

def giveUp(seqNum):
    print(f"Error: Retried sending packet {seqNum} five times with no ACK")

#Does a single try of receiving packet in a non-blocking way
#Updates ACKS if packet found
def receiveACK(serversocket):
    try:
        packet, address = serversocket.recvfrom(MAX_BYTES)
        outerHeader, payload = decapsulate(packet)
        header = struct.unpack_from("!cII",payload)
        assert(header[0]== b'A')
        ACKS[header[1]] = True
    except socket.error as e:
        err = e.args[0] 
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            pass
        else:
            # a "real" error occurred
            print(e)


def makeDataPacket(bytes, sequence_num):
    return struct.pack(f"!cII{len(bytes)}s",b'D',sequence_num,len(bytes),bytes)

def makeEndPacket():
    return struct.pack(f"!cII",b'E',0,0)

def makePacket(requesterIP,requesterPort, bytes, sequence_num,priority,ownPort):
    payload = makeDataPacket(bytes,sequence_num)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encapsulate(priority,ownIP,ownPort,requesterIP,requesterPort,payload)
    return packet

def sendPacket(emulatorHostname,emulatorPort,packet):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    sock.sendto(packet, (emulatorHostname, emulatorPort))

    #Print information
    if(not SUPRESSOUTPUT):
        header,payload = decapsulate(packet)
        innerHeader = struct.unpack_from("!cII",payload)
        section = payload[9:]
        printData(socket.inet_ntoa(header[3]),innerHeader[1],section)


def sendEnd(requesterIP,requesterPort,emulatorHostname,emulatorPort,priority,ownPort):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encapsulate(priority,ownIP,ownPort,requesterIP,requesterPort,makeEndPacket())
    sock.sendto(packet, (emulatorHostname, emulatorPort))
        

def printData(address,sequence,section):
    print("DATA Packet")
    print("send time: ",datetime.utcnow())
    print("requester addr: ",address)
    print("Sequence num: ",sequence)
    print("length: ",len(section))
    print("payload: ",section.decode('utf-8')[0:min(len(section),4)])
    print("")

def printEnd(address, sequence):
    print("END Packet")
    print("send time: ",datetime.utcnow())
    print("requester addr: ",address)
    print("Sequence num: ",sequence)
    print("length: ",0)
    print("payload: ")
    print("")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port")
    parser.add_argument("-g", "--requester_port")
    parser.add_argument("-r", "--rate")
    parser.add_argument("-q", "--seq_no") #deprecated
    parser.add_argument("-l", "--length")
    parser.add_argument("-f", "--f_hostname")
    parser.add_argument("-e", "--f_port")
    parser.add_argument("-i", "--priority")
    parser.add_argument("-t", "--timeout")
    args = parser.parse_args()
    serversocket = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    serversocket.bind((socket.gethostname(), int(args.port)))

    filename, address, window, header = receiveRequest(serversocket)
    serversocket.setblocking(False)
    timeoutMilliseconds = int(args.timeout)
    totalTransmissions = 0
    normalTransmissions = 0

    sequence = 1
    with open(filename,"r+b") as file:
        bytes = bytearray(file.read())
        buffer = []
        for i in range(0,len(bytes),int(args.length)):
            normalTransmissions +=1
            totalTransmissions+=1

            section = bytes[i:min(i+int(args.length),len(bytes))]
            buffer.append(makePacket(header[1],int(args.requester_port),section,sequence,int(args.priority),int(args.port)))
            sequence+=1
        
        times = [0 for i in range(len(buffer))]
        resendCount = [0 for i in range(len(buffer))]
        for w in range(0,len(buffer),window):
            for i in range(w,min(w+window,len(buffer))):
                sendPacket(args.f_hostname,int(args.f_port),buffer[i])
                times[i] = datetime.utcnow().timestamp() * 1000
                resendCount[i] = 0
                time.sleep(1.0/int(args.rate))


            done = False
            
            while(not done):
                done = True
                for i in range(w,min(w+window,len(buffer))):
                    now = datetime.utcnow().timestamp() * 1000
                    receiveACK(serversocket)
                    if(not ACKS[i+1] and resendCount[i] <= 5):
                        done = False
                    if(not ACKS[i+1] and resendCount[i] <5 and now - times[i]>timeoutMilliseconds):
                        # print("Resending packet ",i+1)
                        totalTransmissions+=1
                        sendPacket(args.f_hostname,int(args.f_port),buffer[i])
                        times[i] = datetime.utcnow().timestamp() * 1000
                        resendCount[i]+=1
                        time.sleep(1.0/int(args.rate))  
                        if(resendCount[i]==5):
                            giveUp(i+1)

            #print("DONE!")


                
        sendEnd(header[1],int(args.requester_port),args.f_hostname,int(args.f_port),int(args.priority),int(args.port))
        if(not SUPRESSOUTPUT): 
            printEnd(address,sequence)

    print("Percent of packets lost: ",(totalTransmissions-normalTransmissions)/totalTransmissions*100,"%")
        

    serversocket.close()
