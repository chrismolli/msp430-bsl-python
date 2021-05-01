# msp430-bsl-python
Implementation of the MSP430 BSL protocol for flashing and verification. A Teensy/Arduino is needed to provide a Serial Interface as well as triggering the sequence for entering the BSL.

## Usage
You will need a Teensy/Arduino device with at least two Serial (UART) ports to use the BSL flasher.

Make sure `msp430-elf-objcopy`is visible on the path.

1. Install Teensy FW on Teensy or Arduino Interface device
2. Replug Interface device before every flash
3. Invoke `python3 flash.py binary`to flash a binary to your MSP430 device. ELF32 files will be automatically flattend.

## Interface Device Connection
The following connections need to be made. The Teensy (or Arduino) works as a interface to forward UART in both directions, will invoking the BSL when reset.

[**Host/Laptop**] <-USB-> [**Teensy**] <-UART+GPIO-> [**MSP430**]

The `PIN 10` is connected to the `TEST`, `PIN 11` is connected to `SRST`. `PIN 0` connects to `BSL RX`, `PIN 1` connects to `BSL TX`.
