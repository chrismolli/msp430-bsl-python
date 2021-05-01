from lib.msp430_bsl import BSL, Msgs
import sys
import os
from tqdm import tqdm
from time import sleep

# settings
start_address = 0x004400

# open port
bootloader = BSL("/dev/tty.usbmodem73260101",verbose=True)
sleep(1)

# unlock chip
res = bootloader.unlock()
if res is Msgs.SUCCESS:
    print("Successfully unlocked BSL!")
else:
    try:
        print(f"Could not unlock BSL ({res.name})")
    except:
        print(f"Could not unlock BSL ({res})")

# jump to start
bootloader.load_pc(start_address)
