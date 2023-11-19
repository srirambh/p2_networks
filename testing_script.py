import os
import socket
import subprocess
import time
import sys
def getPort():
    for i in range(2049, 65536):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((socket.gethostname(), i))   
        except socket.error as e:
            continue
        sock.close()
        yield str(i)
    yield -1

gen = getPort()

#Simple sender to requester with no delay, no loss
def test1():

    r1,s1,g1 = next(gen), next(gen), next(gen)
    os.chdir("test1")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 0 0\n")

    output = sys.stdout
    os.chdir("sender")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "100"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../sender/file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 1 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 1 failed\e[0m"])

#Requester, sender, multiple emulators
def test2():
    r1,s1,g1,g2 = next(gen), next(gen), next(gen), next(gen)
    os.chdir("test2")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {g2} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 0 0\n")
        f.write(f"{socket.gethostname()} {g2} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 0 0\n")
        f.write(f"{socket.gethostname()} {g2} {socket.gethostname()} {s1} {socket.gethostname()} {g1} 0 0\n")


    output = sys.stdout
    os.chdir("sender")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "100" , "-f", "table1.txt", "-l", "log02"], stdout=output, stderr=subprocess.STDOUT)
    p3 = subprocess.Popen(['python3', '../emulator.py', "-p", g2, "-q", "100" , "-f", "table1.txt", "-l", "log12"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    p3.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../sender/file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 2 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 2 failed\e[0m"])

#Test two senders, one requester, no delay, no loss
def test3():
    r1,s1,g1,s2 = next(gen), next(gen), next(gen), next(gen)
    os.chdir("test3")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
        f.write(f"file.txt 2 {socket.gethostname()} {s2}\n")

    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s2} {socket.gethostname()} {s2} 0 0\n")


    output = sys.stdout
    os.chdir("sender1")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir("../sender2")

    subprocess.Popen(['python3', '../../sender.py',"-p", s2, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)

    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 3 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 3 failed\e[0m"])

#Test two senders through three emulators
def test4():
    r1,s1,g1,s2,g2,g3 = next(gen), next(gen), next(gen), next(gen),next(gen),next(gen)
    os.chdir("test4")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
        f.write(f"file.txt 2 {socket.gethostname()} {s2}\n")

    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {g2} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s2} {socket.gethostname()} {g3} 0 0\n")
        f.write(f"{socket.gethostname()} {g2} {socket.gethostname()} {r1} {socket.gethostname()} {g1} 0 0\n")
        f.write(f"{socket.gethostname()} {g3} {socket.gethostname()} {r1} {socket.gethostname()} {g1} 0 0\n")
        f.write(f"{socket.gethostname()} {g2} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 0 0\n")
        f.write(f"{socket.gethostname()} {g3} {socket.gethostname()} {s2} {socket.gethostname()} {s2} 0 0\n")


    output = sys.stdout
    os.chdir("sender1")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g2, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir("../sender2")

    subprocess.Popen(['python3', '../../sender.py',"-p", s2, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g3, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)

    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    p3 = subprocess.Popen(['python3', '../emulator.py', "-p", g2, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    p4 = subprocess.Popen(['python3', '../emulator.py', "-p", g3, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    p3.terminate()
    p4.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 4 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 4 failed\e[0m"])


#Test delay: Should reach resend limit, but still receive correct file
def test5():

    r1,s1,g1 = next(gen), next(gen), next(gen)
    os.chdir("test5")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 200 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 0 0\n")

    output = sys.stdout
    os.chdir("sender")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "100"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../sender/file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 5 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 5 failed\e[0m"])


#Test queue: Should drop some packets
def test6():

    r1,s1,g1 = next(gen), next(gen), next(gen)
    os.chdir("test6")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 200 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 0 0\n")

    output = sys.stdout
    os.chdir("sender")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "4" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../sender/file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 6 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 6 failed\e[0m"])


#Test two senders, one with delay and lower priority. One should have loss, the other should not.
def test7():
    r1,s1,g1,s2 = next(gen), next(gen), next(gen), next(gen)
    os.chdir("test7")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
        f.write(f"file.txt 2 {socket.gethostname()} {s2}\n")

    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 500 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s2} {socket.gethostname()} {s2} 0 0\n")


    output = sys.stdout
    os.chdir("sender1")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir("../sender2")

    subprocess.Popen(['python3', '../../sender.py',"-p", s2, "-g" , r1, "-r", "100", "-q", "1", "-l" , "10", "-f" , socket.gethostname(), "-e" , g1, "-i", "2" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)

    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "100" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 7 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 7 failed\e[0m"])



#Test two senders, one with delay and lower priority. One should have loss, the other should not. There should be drops in log
def test8():
    r1,s1,g1,s2 = next(gen), next(gen), next(gen), next(gen)
    os.chdir("test8")
    if not os.path.exists("requester"):
        os.mkdir("requester")
    with open("requester/tracker.txt", "w+") as f:
        f.write(f"file.txt 1 {socket.gethostname()} {s1}\n")
        f.write(f"file.txt 2 {socket.gethostname()} {s2}\n")

    with open("table1.txt", "w+") as f:
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {r1} {socket.gethostname()} {r1} 0 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s1} {socket.gethostname()} {s1} 100 0\n")
        f.write(f"{socket.gethostname()} {g1} {socket.gethostname()} {s2} {socket.gethostname()} {s2} 0 0\n")


    output = sys.stdout
    os.chdir("sender1")
    print("Running Sender")
    subprocess.Popen(['python3', '../../sender.py',"-p", s1, "-g" , r1, "-r", "100", "-q", "1", "-l" , "2", "-f" , socket.gethostname(), "-e" , g1, "-i", "3" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)
    os.chdir("../sender2")

    subprocess.Popen(['python3', '../../sender.py',"-p", s2, "-g" , r1, "-r", "100", "-q", "1", "-l" , "2", "-f" , socket.gethostname(), "-e" , g1, "-i", "2" , "-t", "1000"], stdout=output, stderr=subprocess.STDOUT)

    os.chdir('..')

    time.sleep(1)
    print("Running emulator")
    p2 = subprocess.Popen(['python3', '../emulator.py', "-p", g1, "-q", "4" , "-f", "table1.txt", "-l", "log"], stdout=output, stderr=subprocess.STDOUT)
    time.sleep(1)
    print("Running requester")
    os.chdir("requester")
    p1 = subprocess.Popen(['python3', "../../requester.py", "-p", r1, "-f",socket.gethostname(), "-e", g1, "-o" , "file.txt", "-w", "10"], stdout=output, stderr=subprocess.STDOUT)
    while(p1.poll() is None):
        pass
    p2.terminate()
    sys.stdout.flush()
    p = subprocess.Popen(["diff", "file.txt", "../file.txt"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    if out == None or len(out) == 0:
        subprocess.Popen(["echo", "-e" , "\e[92mtest 8 passed\e[0m"])
    else:
        print(out)
        subprocess.Popen(["echo", "-e" , "\e[31mtest 8 failed\e[0m"])




if __name__ == "__main__":
    for i in ["test" + str(i) for i in range(7,9)]:
        globals()[i]()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        