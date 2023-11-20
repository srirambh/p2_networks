import argparse 
import socket
import struct
import csv
from collections import OrderedDict
from collections import defaultdict
from datetime import datetime
from datetime import timedelta

def decapsulate(packet):
    header = struct.unpack_from("!B4sH4sHI",packet)
    length = header[5]
    return header, struct.unpack_from(f"!{length}s", packet, offset=17)[0]

def sortTracker():
    with open("tracker.txt", "r") as f:
        reader = csv.reader(f,delimiter=' ')
        dic = defaultdict(list)
        for r in reader:
            dic[r[0]].append((int(r[1]), r[2], int(r[3])))
        
        for key in dic.keys():
            dic[key] = sorted(dic[key], key = lambda x: x[0])
        return dic


def receiveData(s, numSend, f_port, e_name , e_port):
    reqIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    d = defaultdict(dict)
    size = numPackets = defaultdict(int)
    start_t = datetime.utcnow()
    
    end = 0
    while end != numSend:
        packet, addr = s.recvfrom(10000)
        second_header, payload = decapsulate(packet)

        if(second_header[3] != reqIP):
            continue
        header = struct.unpack_from("!cII",payload)
        length = header[2]
        size[(second_header[1], second_header[2])] += length

        if header[0] != b'E':
            numPackets[(second_header[1], second_header[2])] += 1 
            received = struct.unpack_from(f"!{length}s", payload, offset=9)[0].decode('utf-8')

            d[(second_header[1],second_header[2])][header[1]] = received

            data = struct.pack(f"!cII",b'A', header[1], 0)
            currPack = struct.pack(f"!B4sH4sHI{len(data)}s", 1, reqIP, f_port, 
                                 second_header[1], second_header[2], len(data), data)
            s.sendto(currPack, (e_name, e_port))

        else:
            end +=1
            end_t = datetime.utcnow()
            milliseconds = (end_t - start_t)/timedelta(milliseconds=1)
            print("END Packet")
            print("send time: ",datetime.utcnow())
            print("requester addr: ", socket.inet_ntoa(second_header[1]))
            print("Sequence num: ", header[1])
            print()
            print("-------SUMMARY-------")
            print("Sender addr: ",socket.inet_ntoa(second_header[1]))
            print("Total Data packets: ", numPackets[(second_header[1], second_header[2])])
            print("Total Data bytes: ", size[(second_header[1], second_header[2])])
            print("Average packets/second: ", 1000 * numPackets[(second_header[1], second_header[2])] / milliseconds)
            print("Duration: ", milliseconds, " ms")
            print("--------------------\n")

    return d


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-p", "--port", help='Input requester port')
    p.add_argument("-o", "--fileoption")
    p.add_argument("-f", "--f_hostname", help='Input host name for the emulator')
    p.add_argument("-e", "--f_port", help='Input port number for the emulator')
    p.add_argument("-w", "--window", help='Input requester window size')
    args = p.parse_args()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    reqIP = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
    sock.bind((socket.gethostname(), int(args.port)))
    with open(args.fileoption, "w+") as f:
        d = sortTracker()
        numSenders = len(d[args.fileoption])
        for i in d[args.fileoption]: # send the req
            id = i[0]
            destIP = socket.inet_aton(socket.gethostbyname(i[1]))       
            fileBytes = bytes(args.fileoption,'utf-8')
            payload = struct.pack(f"!cII{len(fileBytes)}s", b'R', 0, int(args.window), fileBytes)
            packet = struct.pack(f"!B4sH4sHI{len(payload)}s", 1, reqIP, int(args.port), destIP, i[2], len(payload), payload)
            sock.sendto(packet, (args.f_hostname, int(args.f_port)))

        received = receiveData(sock, numSenders, int(args.port), args.f_hostname, int(args.f_port))
        with open(args.fileoption, "a") as f:
            for i in d[args.fileoption]:
                for k, v in OrderedDict(sorted(received[socket.inet_aton(socket.gethostbyname(i[1])), i[2]].items())).items():
                    f.write(v)
