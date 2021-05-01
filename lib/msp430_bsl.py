"""
    @title  msp430_bsl
    @author Christian Mollière
    @date   30/04/2021
    @brief  Implementation of the TI MSP430 BSL protocoll
"""

import binascii
from enum import IntEnum
import serial
from time import sleep

# HEADER LENGTH2B [CMD1B D1 ...] CRC2B
header = 0x80
message = 0x3b
data = 0x3a

"""
    BSL Enumerations
"""
class Cmds(IntEnum):
    WRITE      = 0x10
    UNLOCK     = 0x11
    MASS_ERASE = 0x15
    CRC_CHECK  = 0x16
    LOAD_PC    = 0x17
    READ       = 0x18
    VERSION    = 0x19
    CHG_BAUD   = 0x52

class Acks(IntEnum):
    ACK                 = 0x00
    HEADER_INCORRECT    = 0x51
    CHECKSUM_INCORRECT  = 0x52
    PACKET_SIZE_ZERO    = 0x53
    PACKET_TOO_BIG      = 0x54
    UNKNOWN             = 0x55
    UNKNOWN_BAUDRATE    = 0x56
    PACKET_SIZE_ERR     = 0x57

class Msgs(IntEnum):
    SUCCESS                = 0x00
    MEM_WRITE_CHECK_FAILED = 0x01
    BSL_LOCKED             = 0x04
    BSL_INCORRECT_PASSWORD = 0x05
    UNKNOWN_COMMAND        = 0x06

class BaudRates(IntEnum):
    b9k6     = 0x02,
    b19k2    = 0x03,
    b38k4    = 0x04,
    b57k6    = 0x05,
    b115k2   = 0x06

baudrates = {
    BaudRates.b9k6   : 9600,
    BaudRates.b19k2  : 19200,
    BaudRates.b38k4  : 38400,
    BaudRates.b57k6  : 57600,
    BaudRates.b115k2 : 115200,
}

"""
    Class
"""
class BSL():
    """
        BSL defines commands for the MSP430 BSL interface.
        Upon initialization a port is defined on which the cmds
        will be send.
    """

    """
        Variables
    """
    ser = None
    test_mode = False
    verbose = False

    """
        Decorators
    """
    def command(func):
        """
            sends command and receives
        """
        def _decorator(self, *args, **kwargs):
            # get cmd and wrap into bsl header
            cmd = wrap(func(self, *args, **kwargs))
            # write cmd to serial
            if self.test_mode:
                print(f"TESTMODE ({Cmds(cmd[3]).name}) " + ''.join('{:02x}'.format(x) for x in cmd))
                return ""
            else:
                if self.verbose:
                    print(f"Sending ({Cmds(cmd[3]).name}) " + ''.join('{:02x}'.format(x) for x in cmd))
                self.ser.write(cmd)
            # set new baud rate if necessary
            if Cmds(cmd[3]) is Cmds.CHG_BAUD:
                try:
                    settings = {'baudrate': baudrates[BaudRates(cmd[4])]}
                    self.ser.apply_settings(settings)
                    self.ser.flush()
                except:
                    pass
            # wait for ack
            if Cmds(cmd[3]) not in [Cmds.LOAD_PC, Cmds.CHG_BAUD]:
                # read ack
                try:
                    ack = Acks(self.ser.read(1)[0])
                except:
                    return None
                # check response
                if ack is Acks.ACK:
                    # throw away header byte
                    self.ser.read(1)
                    # read ack length
                    length = self.ser.read(1)[0] | (self.ser.read(1)[0] << 8)
                    # get payload
                    payload = self.ser.read(length)
                    # get crc
                    crc = byte2uint(self.ser.read(2))
                    # check crc
                    if crc != calc_crc(payload):
                        print(f"Received corrupted packet!")
                        return ""
                    # parse returned payload
                    if payload[0] is data:
                        if self.verbose:
                            print(f"Received (DATA) "+ ''.join('{:02x}'.format(x) for x in payload[1:]))
                        return payload[1:]
                    elif payload[0] is message:
                        if self.verbose:
                            print(f"Received (MSG) {Msgs(payload[1]).name}")
                        return Msgs(payload[1])
                    else:
                        return payload
                else:
                    # ack != ok
                    return ack.name
            else:
                # if loadpc not return expected
                return None
        return _decorator

    """
        Methods
    """
    def __init__(self, port, verbose=False):
        """
            Initializes serial port towards MSP430 chip.
            If port is unavailable the object will be using test mode.
            @param port : string, serial port
            @param verbose : boolean, (optional) verbose printing (default False)
            @return BSL object
        """
        self.verbose = verbose
        try:
            self.ser = serial.Serial(port,
                                     baudrate=9600,
                                     bytesize=serial.EIGHTBITS,
                                     stopbits=serial.STOPBITS_ONE,
                                     timeout=1,
                                     parity=serial.PARITY_NONE,
                                     rtscts=0)
        except:
            print(f"Serial port {port} not available, entering test mode.")
            self.test_mode = True

    def close(self):
        """
            closes the serial port
        """
        self.ser.close()

    @command
    def write(self, address, data):
        """
            writes value to specified address
            @param address, address to write to
            @param data : bytearray, data to write (max 256)
            @return acknowledgment or message
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.WRITE)
        cmd.append( address & 0xff )
        cmd.append( (address>>8) & 0xff )
        cmd.append( (address>>16) & 0xff )
        if type(data) in [bytearray,bytes]:
            cmd += data
        else:
            cmd.append(data&0xff)
            cmd.append((data>>8)&0xff)
        return cmd

    @command
    def unlock(self, password=None):
        """
            unlocks the BSL
            @param password : bytearray (optional), 32 bytes to unlock chip
            @return acknowledgment or message
        """
        if password is None:
            password = bytearray.fromhex("".join(["ff" for i in range(32)]))
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.UNLOCK)
        cmd += password
        return cmd

    @command
    def mass_erase(self):
        """
            erase the complete on-chip memory
            @return acknowledgment or message
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.MASS_ERASE)
        return cmd

    @command
    def crc_check(self,address,length):
        """
            calculates the crc for a memory section using CRC16-CITT
            @param address , address to start calculation
            @param length , how many bytes to walk from address
            @return data : bytearray, crc value obtained
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.CRC_CHECK)
        cmd.append( address & 0xff )
        cmd.append( (address>>8) & 0xff )
        cmd.append( (address>>16) & 0xff )
        cmd.append( length & 0xff )
        cmd.append( (length>>8) & 0xff )
        return cmd

    @command
    def load_pc(self,address):
        """
            sets the PC of the chip
            @param address , address to set PC to
            @return None
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.LOAD_PC)
        cmd.append( address & 0xff )
        cmd.append( (address>>8) & 0xff )
        cmd.append( (address>>16) & 0xff )
        return cmd

    @command
    def read(self,address,length):
        """
            reads memory from address with length
            @param address , address to read from
            @param length , bytes to read
            @return data : bytearray, data read
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.READ)
        cmd.append( address & 0xff )
        cmd.append( (address>>8) & 0xff )
        cmd.append( (address>>16) & 0xff )
        cmd.append( length & 0xff )
        cmd.append( (length>>8) & 0xff )
        return cmd

    @command
    def version(self):
        """
            calculates the crc for a memory section using CRC16-CITT
            @return data : bytearray, version string
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.VERSION)
        return cmd

    @command
    def change_baudrate(self, baudrate):
        """
            changes the baudrate of the serial interface in the chip
            @param baudrate : BaudRates, specifies a baudrate byte
            @return None
        """
        cmd = bytearray.fromhex("")
        cmd.append(Cmds.CHG_BAUD)
        cmd.append(baudrate)
        return cmd

    def debug(self):
        print(self.ser.get_settings())

"""
    Helper
"""
def calc_crc(data):
    """
        calculates the CRC16-CITT
        @param data : bytes or bytearray, data to calc crc on
        @return crc value
    """
    return binascii.crc_hqx(data,0xffff)

def wrap(cmd):
    """
        wraps cmd into bsl frame
        @param cmd : bytes or bytearray
        @return bsl frame : bytearray
    """
    frame = bytearray.fromhex(f"{header:02x}")
    length = len(cmd)
    frame.append( length & 0xff )
    frame.append( (length>>8) & 0xff )
    frame += cmd
    crc = calc_crc(cmd)
    frame.append( crc & 0xff )
    frame.append( (crc>>8) & 0xff )
    return frame

def byte2uint(bytes):
    """
       creates integer from bytearray
       @param bytes : bytes or bytearray
    """
    return int.from_bytes(bytes, byteorder='little', signed=False)

"""
    Test section
"""
if __name__ == "__main__":
    pass
