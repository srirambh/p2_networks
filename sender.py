import socket
import time
import argparse
import struct
from datetime import datetime
import errno

packets_rec = {}

def readFile(filename):
    arr = []
    with open(filename, "r+b") as f:
        arr = bytearray(f.read())
    return arr

def decapsulate(packet):
    header = struct.unpack_from("!B4sH4sHI", packet)
    payload = struct.unpack_from(f"!{header[5]}s", packet, offset=17)[0]
    return header, payload    

def receiveReq(sock):
    data, address = sock.recvfrom(10000) # FIX
    header, payload = decapsulate(data)
    request = struct.unpack_from("!cII", payload)
    fname = payload[9:].decode('utf-8')
    return address, header, request[2], fname

def receiveAck(sock):
    try:
        data, address = sock.recvfrom(10000)
        second_header, payload = decapsulate(data)
        header = struct.unpack_from("!cII", payload)
        if(header[0]== b'A'):
            packets_rec[header[1]] = True
        else:
            packets_rec[header[1]] = False
    except socket.error as e:
        if e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK:
            pass

def sendPacket(f_hostname, f_port, packet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (f_hostname, f_port))

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
    server = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    server.bind((socket.gethostname(), int(args.port)))

    address, header, window, filename = receiveReq(server)
    server.setblocking(False)
    timeout = int(args.timeout)
    total = expected = 0
    seq_num = 1
    buf = []
    servIP = ""

    bytes = readFile(filename)
    
    for i in range(0,len(bytes), int(args.length)):
        expected += 1
        total += 1

        sect = bytes[i:min(i+int(args.length),len(bytes))]
        payload = struct.pack(f"!cII{len(sect)}s", b'D', seq_num, len(sect), sect)
        servIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
        packet = struct.pack(f"!B4sH4sHI{len(payload)}s", args.priority, servIP, args.port, 
                             header[1], args.requestor_port, len(payload), payload)
        buf.append(packet)
        seq_num+=1
    
    times = resend = [0] * len(buf)
    for i in range(0,len(buf),window):
        for j in range(i,min(i+window,len(buf))):

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(buf[j], args.f_hostname, args.f_port)

            times[j] = datetime.utcnow().timestamp() * 1000
            resend[j] = 0

            time.sleep(1.0/int(args.rate))


        check = False
        
        while(not check):
            check = True

            for j in range(i, min(i+window,len(buf))):
                curr = 1000 * datetime.utcnow().timestamp()
                receiveAck(server)
                if(not packets_rec[j+1] and resend[j] <= 5):
                    check = False
                if(not packets_rec[j+1] and resend[j] <5 and curr - times[j] > timeout):
                    total += 1
                    sock.sendto(buf[j], (args.f_hostname, int(args.f_port)))
                    times[j] = 1000 * datetime.utcnow().timestamp()
                    resend[j] += 1
                    time.sleep(1.0 / int(args.rate))  
                    if resend[j] == 5:
                        print(f"Error for packet with seq number: {seq_num}")

    servIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    endPkt = struct.pack(f"!B4sH4sHI{len(payload)}s", args.priority, servIP, args.port, 
                             header[1], args.requestor_port, len(payload), payload)
    sock.sendto(endPkt, (args.f_hostname, int(args.f_port)))

    print("Percent of packets lost: ",(total-expected)/total*100,"%")
        

    server.close()
