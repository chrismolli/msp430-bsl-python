import subprocess

tmp_path = "temp.bin"

def elf2bin(fname):
    # check file type
    res = subprocess.run(["file",fname], stdout=subprocess.PIPE)
    if "ELF" in res.stdout.decode('utf-8'):
        # convert and save
        print("Converting elf32-msp430 to binary...")
        subprocess.run(["msp430-elf-objcopy","-I","elf32-msp430","-O","binary",fname,"temp.bin"], stdout=subprocess.PIPE)
    else:
        # save
        subprocess.run(["cp",fname,"temp.bin"], stdout=subprocess.PIPE)
    return "temp.bin"


def clear_tempory_binaries():
    subprocess.run(["rm","temp.bin"], stdout=subprocess.PIPE)
