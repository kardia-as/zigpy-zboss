"""Script that converts a serial log file in a pcap file."""
import argparse
import datetime
import re
import struct

LINKTYPE_ZBOSS_NCP = 292
TX_RX_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    r' \[(DEBUG)\]: (TX|RX): b\'(.+?)\'$')


def hex_to_bytes(hex_str):
    """Convert hex to bytes."""
    return bytes.fromhex(hex_str.replace(':', ''))


def parse_log_file(log_file):
    """Parse the serial log file."""
    packets = []
    with open(log_file, 'r') as f:
        for line in f:
            match = TX_RX_PATTERN.match(line)
            if match:
                timestamp_str, _, direction, hex_data = match.groups()
                timestamp = datetime.datetime.strptime(
                    timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                packet_bytes = hex_to_bytes(hex_data)
                packets.append((direction, packet_bytes, timestamp))
    return packets


class PcapWriter:
    """Class responsible to write in pcap format."""

    def __init__(self, filename, linktype=LINKTYPE_ZBOSS_NCP):
        """Initilialize pcap file and write global header."""
        self.filename = filename
        self.linktype = linktype
        self.fdesc = open(self.filename, "wb")
        magic_number = 0xa1b2c3d4
        self.fdesc.write(struct.pack("<L", magic_number))
        self.fdesc.write(struct.pack("<H", 2))
        self.fdesc.write(struct.pack("<H", 4))
        self.fdesc.write(struct.pack("<L", 0))
        self.fdesc.write(struct.pack("<L", 0))
        self.fdesc.write(struct.pack("<L", 65535))
        self.fdesc.write(struct.pack("<L", self.linktype))

    def write_packet(self, packet_bytes, timestamp):
        """Write a packet with its header."""
        timestamp_sec = int(timestamp.timestamp())
        timestamp_usec = int(timestamp.microsecond)
        self.fdesc.write(struct.pack("<L", timestamp_sec))
        self.fdesc.write(struct.pack("<L", timestamp_usec))
        self.fdesc.write(struct.pack("<L", len(packet_bytes)))
        self.fdesc.write(struct.pack("<L", len(packet_bytes)))
        self.fdesc.write(packet_bytes)

    def close(self):
        """Close pcap file."""
        self.fdesc.close()


def main(log_file, pcap_file):
    """Convert serial log file to pcap file."""
    packets = parse_log_file(log_file)
    pcap_writer = PcapWriter(pcap_file)
    for _, packet_bytes, timestamp in packets:
        pcap_writer.write_packet(packet_bytes, timestamp)
    pcap_writer.close()
    print(f"Wrote {len(packets)} packets to {pcap_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a serial communication log to PCAP format")
    parser.add_argument(
        "log_file", help="Path to the serial communication log file")
    parser.add_argument("pcap_file", help="Path to the PCAP output file")
    args = parser.parse_args()

    main(args.log_file, args.pcap_file)
