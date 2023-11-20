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

def readFile(filename):
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

def sendPack(e_name, e_port, packet):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    sock.sendto(packet, (e_name, e_port))


def sendEnd(priority, requesterIP,requesterPort,emulatorHostname,emulatorPort,ownPort):
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    packet = encap(priority, ownIP, ownPort, requesterIP, requesterPort, struct.pack(f"!cII",b'E',0,0))
    sock.sendto(packet, (emulatorHostname, emulatorPort))
        

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-p", "--port", help='Input sender port')
    p.add_argument("-g", "--requester_port", help='Input requester port for receiver from ports')
    p.add_argument("-r", "--rate", help='Input rate at which packets are sent')
    p.add_argument("-q", "--seq_no", help='Input sequence of packet exchange') 
    p.add_argument("-l", "--length", help='Input length of the payload')
    p.add_argument("-f", "--f_hostname", help='Input host name for the emulator')
    p.add_argument("-e", "--f_port", help='Input emulator port')
    p.add_argument("-i", "--priority", help='Input level of priority for the sent packets')
    p.add_argument("-t", "--timeout", help='Input time for retransmission of lost packets in ms')
    args = p.parse_args()
    sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    sock.bind((socket.gethostname(), int(args.port)))

    header, address, window, filename = receiveRequest(sock)
    
    sock.setblocking(False)
    
    seq_num = 1
    total = 0
    success = 0
    
    bytes = readFile(filename)
    buf = []
    timeout = int(args.timeout)
    for i in range(0, len(bytes), int(args.length)):
        success += 1
        total += 1

        sec = bytes[i : min(i + int(args.length), len(bytes))]
        
        data = struct.pack(f"!cII{len(sec)}s", b'D', seq_num, len(sec), sec)
        send_ip = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
        packet = struct.pack(f"!B4sH4sHI{len(data)}s", int(args.priority), send_ip, int(args.port), 
                             header[1], int(args.requester_port), len(data), data)

        buf.append(packet)
        seq_num += 1
    
    times = [0] * len(buf)
    resend = [0] * len(buf)
    for i in range(0, len(buf), window):
        for j in range(i, min(len(buf), window + i)):
            sendPack(args.f_hostname, int(args.f_port), buf[j])
            print("sending packet to emu")
            times[j] = datetime.utcnow().timestamp() * 1000
            resend[j] = 0
            time.sleep(1.0 / int(args.rate))


        check = False
        
        while(not check):
            check = True
            for j in range(i, min(len(buf), window + i)):
                now = datetime.utcnow().timestamp() * 1000
                handleAck(sock)
                if(not received_req[j+1] and resend[j] <= 5):
                    check = False
                if(not received_req[j+1] and resend[j] <5 and now - times[j] > timeout):
                    total += 1
                    print("sending packet to emu")
                    sendPack(args.f_hostname,int(args.f_port), buf[j])
                    times[j] = 1000 * datetime.utcnow().timestamp()
                    resend[j] += 1
                    time.sleep(1.0 / int(args.rate))  
                    if(resend[j] == 5):
                        print(f"Error: Retried sending packet {i+1} five times with no ACK")

    # def sendEnd(priority, requesterIP,requesterPort,emulatorHostname,emulatorPort,ownPort):
    #     sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    #     ownIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    #     packet = encap(priority, ownIP, ownPort, requesterIP, requesterPort, struct.pack(f"!cII",b'E',0,0))
    #     sock.sendto(packet, (emulatorHostname, emulatorPort))

            
    # sendEnd(int(args.priority), header[1],int(args.requester_port),args.f_hostname,int(args.f_port),int(args.port))

    newsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_ip = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    endData = struct.pack(f"!cII",b'E',0,0)
    packet = struct.pack(f"!B4sH4sHI{len(endData)}s", int(args.priority), send_ip, int(args.port), 
                             header[1], int(args.requester_port), len(endData), endData)
    newsock.sendto(packet, (args.f_hostname, int(args.f_port)))

    print("Percent of packets lost: ", 100 * (total-success) / total, "%")
        

    sock.close()
