from lib.msp430_bsl import BSL, Msgs, calc_crc, byte2uint, BaudRates
from lib.elf_to_binary import elf2bin, clear_tempory_binaries

import sys
import os
from tqdm import tqdm
from time import sleep

"""
    TODOs
    - Speed up baudrate (does not work)
"""

# print info
print("")
print(" **** Started MSP430 BSL Flasher")
print("  *** v0.1")
print("")

# convert file if needed
if len(sys.argv) > 1:
    fname = elf2bin(sys.argv[1])
else:
    print("Missing file path!")
    print("msp430-bsl-flash [<fname> binary or elf]")
    exit()

# settings
start_address = 0x004400
password = None
chunksize = 256

# open port
bootloader = BSL("/dev/tty.usbmodem73260101",verbose=False)
sleep(1)

# unlock chip
res = bootloader.unlock(password)
if res is Msgs.SUCCESS:
    print(f"Successfully unlocked target using {password}!")
else:
    try:
        print(f"Could not unlock BSL ({res.name})")
    except:
        print(f"Could not unlock BSL ({res})")

# show target version
res = bootloader.version()
if type(res) is Msgs:
    print(f"Could not read BSL Version ({res.name})")
else:
    print(f"BSL Version on target: {res[0]:02x} {res[1]:02x} {res[2]:02x} {res[3]:02x}")

# flash
with open(fname,"rb") as binary:
    # read size
    length = os.path.getsize(fname)
    print(f"Flashing 0x{length:06x} bytes to target at 0x{start_address:06x}...")

    # start writing
    address = start_address

    with tqdm(total=length, unit_scale=True) as pbar:
        pbar.set_description("Flashing")

        while address < (start_address + length):
            # print(f"Writing Address 0x{address:06x}")
            # read chunk from binary
            chunk = binary.read(chunksize)
            # write to chip
            res = bootloader.write(address,chunk)
            # check if write ok
            if res != Msgs.SUCCESS:
                print(f"Flashing failed ({res.name})!")
                break
            # increment address
            address += chunksize
            pbar.update(chunksize)

# verify
with open(fname,"rb") as binary:
    print("Verifying code on target...")

    # read size
    length = os.path.getsize(fname)

    # start verifying
    address = start_address

    with tqdm(total=length, unit_scale=True) as pbar:
        pbar.set_description("Verifying")

        while address < (start_address + length):
            # print(f"Writing Address 0x{address:06x}")
            # read chunk from binary
            chunk = binary.read(chunksize)
            crc = calc_crc(chunk)
            # write to chip
            crc_rx = byte2uint(bootloader.crc_check(address,chunksize))
            # print(crc, crc_rx)
            # check if write ok
            if crc != crc_rx:
                print(f"Verification failed at (0x{address:06x})!")
                break
            # increment address
            address += chunksize
            pbar.update(chunksize)

# jump to start
bootloader.load_pc(start_address)

# clean up binaries
clear_tempory_binaries()

print("Successfully finished flashing")
