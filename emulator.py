import argparse 
import socket
import struct
import csv
import random
from datetime import datetime
from collections import defaultdict
import errno

def decapsulate(packet):
    header = struct.unpack_from("!B4sH4sHI", packet)
    payload = struct.unpack_from(f"!{header[5]}s", packet, offset=17)[0]
    return header, payload

def parseTab(hname, fname, port):
    with open(fname, "r") as f:
        dic = defaultdict(lambda : ("",0,0,0)) #Fix this
        reader = csv.reader(f, delimiter=' ')
        for r in reader:
            if int(r[1])==port and r[0]==hname:
                dHost = socket.inet_aton(socket.gethostbyname(r[2]))
                dPort = int(r[3])
                nHost = socket.gethostbyname(r[4])
                nPort = int(r[5])
                delay = int(r[6])/1000.0
                loss = int(r[7])
                dic[(dHost, dPort)] = (nHost, nPort, delay, loss) 
        return dic
    
def logLoss(packet, lfile, message):
    header = decapsulate(packet)[0]
    with open(lfile, "a") as f:
        f.write(message + " \n")
        f.write("Source Address: "+ str(socket.inet_ntoa(header[1])) + " Port: " + str(header[2]) + "\n")
        f.write("Destination Address: " + str(socket.inet_ntoa(header[3])) + " Port: "+ str(header[4]) + "\n")
        f.write("Time of Loss: "+ str(datetime.utcnow()) + "\n")
        f.write("Priority level: "+ str(header[0]) + "\n")
        f.write("Payload Size: " + str(header[5]) + " Bytes\n")
        f.write("-"*50+"\n\n")
    
def sendPacket(n, packet, file, type):
    if(type!=b'E' and random.randint(1,100)<=n[3]):
        logLoss(packet,file,"Random Loss Occurred")
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packet,(n[0], n[1]))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-p", "--port")
    p.add_argument("-q", "--queue_size")
    p.add_argument("-f", "--filename")
    p.add_argument("-l", "--log")
    args = p.parse_args()
    tab = parseTab(socket.gethostname(), args.filename, int(args.port))
    s = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
    s.bind((socket.gethostname(), int(args.port)))
    s.setblocking(0)
    with open(args.log, "w+") as f: #Change
        pass
    pkts  = []
    delay = False
    queue = [[],[],[]]
    while(True):
        if len(pkts) > 0 and datetime.utcnow().timestamp() * 1000 >= pkts[0][0] and delay:
            delay = False
            sendPacket(*pkts[0][1:])
            pkts.pop(0)
        try:
            packet, addr = s.recvfrom(10000)
        except socket.error as err:
            e = err.args[0]
            if not e == errno.EAGAIN and not e == errno.EWOULDBLOCK:
                print(err)
                break
            else:
                pass
        else:
            header, payload = decapsulate(packet)
            prior = header[0]
            if(not tab[(header[3], header[4])]):
                logLoss(packet,args.log,"no forwarding entry found")
                continue
            if(struct.unpack_from("!cII", payload)[0] == b'E' or len(queue[prior-1]) < int(args.queue_size)):
                queue[prior-1].append(packet)

            else:
                logLoss(packet,args.log, f"priority queue {prior} was full")
        
        if(not delay): #Step 4
            for p in range(3):
                if(queue[p]):
                    delay=True
                    sentPkt = queue[p].pop(0)
                    header, payload = decapsulate(sentPkt)
                    pkts.append([(datetime.utcnow().timestamp() * 1000) + (tab[(header[3], header[4])][2]*1000), tab[(header[3], header[4])],sentPkt,args.log,struct.unpack_from("!cII", payload)[0]])
                    break
            
        



