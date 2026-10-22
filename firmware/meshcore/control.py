"""USB controls for the experimental on-bike module; never sets channel secrets."""
import argparse
import json
import struct
import time

def command(args):
    if args.action == 'status':
        return bytes([0xE1, 1])
    if not 15 <= args.interval <= 1440 or not 1 <= args.channel <= 7:
        raise ValueError('Interval must be 15–1440 minutes; channel must be 1–7.')
    if args.action == 'enable' and not args.private_channel:
        raise ValueError('Confirm that this channel was configured privately with --private-channel.')
    return struct.pack('<BBBBBHB', 0xE0, 1, args.action == 'enable', args.location,
                       args.channel, args.interval, args.private_channel)

def read_exact(port, size, deadline):
    result = b''
    while len(result) < size:
        if time.monotonic() >= deadline:
            raise TimeoutError('No complete reply from the Bee-Link firmware.')
        chunk = port.read(size-len(result))
        if chunk: result += chunk
    return result

def receive(port):
    deadline = time.monotonic()+6
    while time.monotonic() < deadline:
        if read_exact(port, 1, deadline) != b'>': continue
        length, = struct.unpack('<H', read_exact(port, 2, deadline))
        if length > 512: raise ValueError('Invalid companion frame length.')
        data = read_exact(port, length, deadline)
        if len(data) == 12 and data[:2] == bytes([0xE0, 1]):
            return {'enabled':bool(data[2]), 'include_location':bool(data[3]), 'channel':data[4],
                    'interval_minutes':data[5] | (data[6]<<8),
                    'status':['disabled','waiting','skipped','submitted','failed'][data[7]] if data[7] < 5 else 'unknown',
                    'next_attempt_in_seconds':struct.unpack('<I',data[8:12])[0]}
        if data and data[0] == 1:
            raise ValueError('Firmware rejected settings; check the private channel and module version.')
    raise TimeoutError('No Bee-Link status reply.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('port', help='USB serial path or COM port')
    parser.add_argument('action', choices=['status','enable','disable'])
    parser.add_argument('--channel', type=int, default=1)
    parser.add_argument('--interval', type=int, default=15)
    parser.add_argument('--location', action='store_true')
    parser.add_argument('--private-channel', action='store_true')
    args = parser.parse_args()
    data = command(args)
    import serial
    # Avoid deliberate DTR/RTS reset on port opening. The OS/driver can still vary.
    port = serial.Serial(port=None, baudrate=115200, timeout=0.25)
    port.dtr = False; port.rts = False; port.port = args.port
    try:
        port.open()
        port.write(b'<'+struct.pack('<H',len(data))+data)
        port.flush()
        print(json.dumps(receive(port), indent=2))
    finally:
        port.close()

if __name__ == '__main__':
    main()
