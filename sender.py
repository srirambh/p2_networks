import argparse
import socket
import struct
from datetime import datetime
from datetime import timedelta
import time
import errno
from collections import defaultdict

received_req = defaultdict(bool)

def encap(priority, src_ip, src_port, dest_ip, dest_port,payload):
    packet = struct.pack(f"!B4sH4sHI{len(payload)}s",priority,src_ip,src_port,dest_ip,dest_port,len(payload),payload)
    return packet


def decap(packet):
    header = struct.unpack_from("!B4sH4sHI",packet)
    length = header[5]
    data = struct.unpack_from(f"!{length}s", packet, offset=17)[0]
    return header, data

def readFile(filename, b):
    arr = []
    with open(filename, "r+b") as f:
        arr = bytearray(f.read())
    return arr


def receiveRequest(server):
    data, address = server.recvfrom(10000)
    second_header, payload = decap(data)
    request = struct.unpack_from("!cII",payload)
    window = request[2]
    f_name = payload[9:].decode('utf-8')
    return second_header, address, window, f_name

def handleAck(server):
    try:
        packet = server.recvfrom(10000)[0]
        data = decap(packet)[1]
        header = struct.unpack_from("!cII", data)
        received_req[header[1]] = True

    except socket.error as e:
        if e.args[0]  == errno.EAGAIN or e.args[0]  == errno.EWOULDBLOCK:
            pass

def makePacket(priority, reqIP, reqPort, bytes, seq_num, ownPort):
    payload = struct.pack(f"!cII{len(bytes)}s", b'D', seq_num, len(bytes), bytes)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encap(priority, ownIP, ownPort, reqIP, reqPort, payload)
    return packet

def sendPacket(e_name, e_port, packet):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    sock.sendto(packet, (e_name, e_port))


def sendEnd(priority, requesterIP,requesterPort,emulatorHostname,emulatorPort,ownPort):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encap(priority, ownIP, ownPort, requesterIP, requesterPort, struct.pack(f"!cII",b'E',0,0))
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

    header, address, window, filename = receiveRequest(serversocket)
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
            buffer.append(makePacket(int(args.priority), header[1],int(args.requester_port),section,sequence,int(args.port)))
            sequence+=1
        
        times = [0 for i in range(len(buffer))]
        resendCount = [0 for i in range(len(buffer))]
        for w in range(0,len(buffer),window):
            for i in range(w,min(w+window,len(buffer))):
                sendPacket(args.f_hostname, int(args.f_port), buffer[i])
                print("sending packet to emu")
                times[i] = datetime.utcnow().timestamp() * 1000
                resendCount[i] = 0
                time.sleep(1.0/int(args.rate))


            done = False
            
            while(not done):
                done = True
                for i in range(w,min(w+window,len(buffer))):
                    now = datetime.utcnow().timestamp() * 1000
                    handleAck(serversocket)
                    if(not received_req[i+1] and resendCount[i] <= 5):
                        done = False
                    if(not received_req[i+1] and resendCount[i] <5 and now - times[i]>timeoutMilliseconds):
                        # print("Resending packet ",i+1)
                        totalTransmissions+=1
                        print("sending packet to emu")
                        sendPacket(args.f_hostname,int(args.f_port),buffer[i])
                        times[i] = datetime.utcnow().timestamp() * 1000
                        resendCount[i]+=1
                        time.sleep(1.0/int(args.rate))  
                        if(resendCount[i]==5):
                            print(f"Error: Retried sending packet {i+1} five times with no ACK")

            #print("DONE!")


                
        sendEnd(int(args.priority), header[1],int(args.requester_port),args.f_hostname,int(args.f_port),int(args.port))

    print("Percent of packets lost: ",(totalTransmissions-normalTransmissions)/totalTransmissions*100,"%")
        

    serversocket.close()
