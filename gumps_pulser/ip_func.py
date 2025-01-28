import time
import datetime
import codecs
import binascii
import json
import numpy as np



help_array = """
h   :    help
p   :    get stored data
a   :    asynchronus sampling
s   :    synchronus sampling
r   :    restore ADC buffer
t   :    twiddle LEDs
i   :    get configuration
o   :    set configuration
d   :    synchronus multiple windows sampling with decimal value transfer
x   :    synchronus multiple windows sampling with   HEX   value transfer
c   :    Pulser_Reciever
g   :    plot data
f1  :    butter filter
w   :    save data in file
"""

# flushes serial input and output of handle


def flush(ser):
    try:
        ser.flushInput()
        ser.flushOutput()
    except:
        print("error in flush")


def read_ser_large(ser, read_char):
    # flush(ser)
    data = ''
    k = np.zeros(48000)  # number of samples in one cycle of while loop
    ser.write(str.encode(read_char))
    while(not ser.inWaiting()):
        pass
    tic = time.time()
    time.sleep(0.001)
    i = 0
    n = ser.inWaiting()
    while (n):
        k[i] = n
        data += ser.read(n)
        i += 1
        time.sleep(0.005)
        n = ser.inWaiting()
    tic = time.time() - tic
    data1 = data[22:-4]
    data2 = np.zeros(len(data1)/2)
    # convert to integer
    for i in range(len(data2)):
        data2[i] = int(str(int(data1[2*i].encode('hex'), 16)) +
                       str(int(data1[2*i+1].encode('hex'), 16)))

    return data2


def setup_delay(ser):
    # needed to make sure mc does not have any unfinished data
    # transfer left
    flush(ser)
    tic = time.time()
    print("wait for few seconds")
    while(1):
        n = ser.inWaiting()
        while(n):
            tic = time.time()
            ser.read(n)
            n = ser.inWaiting()
        if((time.time()-tic) > 5):
            break
    print("thank you for waiting")


def get_confg(ser):
    print("enter config")
    ser.read(ser.inWaiting())
    while(not ser.write(str.encode('i'))):
        pass
    time.sleep(0.05)
    info = ser.read(ser.inWaiting())
    info = info.decode(encoding = 'UTF-8', errors = 'strict')
    print(info)
    buf = int(info[3:11])
    now = int(info[11:15])
    return [buf, now]


def set_confg(ser, buf_set, now_set):

    _extracted_from_set_confg_4(ser, 'b', buf_set)
    _extracted_from_set_confg_4(ser, 'q', now_set)

def _extracted_from_set_confg_4(ser, arg1, arg2):
    #buf = raw_input("choose buffer size: 1->100,2->1000,3->10000(F),4->48000(F): ")
    while not ser.write(str.encode(arg1)):
        pass
    time.sleep(0.01)
    while not ser.write(str.encode(arg2)):
        pass
    time.sleep(0.01)
    ser.read(ser.inWaiting())


def pulsar_receiver(ser, buf, now):
    # expects hexadecimal characters in serial comm
    k = np.zeros(48000)
    i = 0
    rec_noc = 0
    data = ''

    # maximum characters expected
    max_noc = buf*2 + 17

    ser.write(str.encode('c'))
    n = ser.inWaiting()
    rec_noc += n
    timeout = 1100
    time_start = time.time()
    while (time.time() < time_start + timeout):
        if (n):
            data += (ser.read(n)).decode(encoding = 'UTF-8', errors = 'strict')
        time.sleep(0.01)
        n = ser.inWaiting()
        k[i] = n
        if (n):
            rec_noc += n
            if(rec_noc == max_noc):
                break
            i += 1
    data1 = data[3:]  # remove initial characters
    data2 = np.zeros(buf)
    print("DATA aquisation done ...")
    # convert to integer
    print("Converting to Integer:" + str(datetime.datetime.now()))
    for i in range(buf):
        data2[i] = int(str(int(codecs.encode(str.encode(data1[2*i]), 'hex'), 16)) +
                       str(int(codecs.encode(str.encode(data1[2*i+1]), 'hex'), 16)).zfill(2))
    data2 = ((data2)/4096)*3
    #save_data3(data2)
    print("Saving data to file .....")
    print(data2)
    print("Aquisation done:" + str(datetime.datetime.now()))
    return data2


def save_data_json(data):
    file = "Data_" + datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".json"
    with open(file, 'w') as outfile:
        json.dump(data, outfile)


def save_data3(data):
    file = "Data_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "raw.txt"
    with open(file, 'w') as f:
        string_data = "".join(str(p)+'\n' for p in data)
        f.write(string_data)


# Upload a single set of data

def upload_data(folder_path):
    upload_data_to_server(folder_path)
