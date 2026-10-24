"""Read-only STS servo ping scan. Does not write registers or command motion."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / '.servo_tools'))
import serial


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM5'
    found = []
    with serial.Serial(port, 1_000_000, timeout=0.025, write_timeout=1) as bus:
        time.sleep(0.2)
        print(f'Scanning {port} at 1000000 baud using PING only.', flush=True)
        for servo_id in range(254):
            bus.reset_input_buffer()
            packet = bytes([255, 255, servo_id, 2, 1, (~(servo_id + 3)) & 255])
            bus.write(packet)
            bus.flush()
            response = bus.read(32)
            # Locate a complete, checksum-valid status frame; ignore TX echo.
            for i in range(len(response) - 5):
                if response[i:i+3] != bytes([255, 255, servo_id]):
                    continue
                length = response[i+3]
                frame = response[i:i+length+4]
                if length < 2 or len(frame) != length + 4 or frame == packet:
                    continue
                if sum(frame[2:]) & 255 == 255:
                    print(f'Found servo ID: {servo_id}; status: {frame[4]}', flush=True)
                    found.append(servo_id)
                    break
        print(f'Scan complete. IDs: {found}' if found else 'Scan complete. No servo responded.')


if __name__ == '__main__':
    main()
