import os
import signal
import subprocess
from signal import SIGTERM
from subprocess import CalledProcessError, Popen
from typing import Optional
from ipaddress import ip_network, IPv4Network, IPv6Network
from utils.core.command_runner import run_command_str, run_python
from utils.core.logs import print_debug, print_error, print_success, print_warning, print_info
from netfilterqueue import NetfilterQueue
import socket
from utils.network.iptables import (
    add_nfqueue_rule_tagged,
    ensure_nfqueue_rule_using_ipset,
    heartbeat_touch,
)

def wait_ready_signal(queue_num:int, timeout:int=5):
    print_debug(f"Waiting for spoofer to signal ready on queue {queue_num} with timeout {timeout} seconds")
    sock_path = f'/tmp/spoofer_ready_{queue_num}.sock'
    if os.path.exists(sock_path):
        os.remove(sock_path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(sock_path)
    server.settimeout(timeout)  # Use the provided timeout

    try:
        data, _ = server.recvfrom(1024)
        if data == b'ready':
            print_debug("Spoofer signaled ready!")
    except:
        print_warning("Timed out")
    finally:
        server.close()
        os.remove(sock_path)

class SipPacketSpoofer:
    """
    Class to handle packet spoofing using iptables and netfilterqueue.
    """

    def __init__(self, attack_queue_num: int,
                 spoofed_subnet: str,
                 victim_port: int = 0,
                 victim_ip: str = "",
                 attacker_port: int = 0,
                 open_window: bool = False,
                 session_uid: str | None = None,
                 dry_run: bool = False,
                 verbosity: str = "info"):
        self.spoofed_subnet : IPv4Network | IPv6Network = ip_network(spoofed_subnet)  # Format : xxx.xxx.0/24
        self.attack_queue_num : int = attack_queue_num
        self.attacker_port : int = attacker_port
        self.victim_ip : str = victim_ip
        self.victim_port : int = victim_port
        self.dry_run : bool = dry_run
        self.verbosity : str = verbosity

        self.next_ip_number: int = 0
        self.spoofed_ips : list[str] = [str(ip) for ip in self.spoofed_subnet.hosts()]  # List of spoofed IPs in the subnet
        self.netfilter_spoofing_queue: Optional[NetfilterQueue] = None
        self.spoofer_process: Optional[Popen[bytes]] = None
        self.spoofer_pid: Optional[int] = None
        self.open_window: bool = open_window
        self.session_uid: str | None = session_uid
        self._ipset_name: str | None = None

    def set_session_uid(self, session_uid: str) -> None:
        """Set the session UID for this spoofer."""
        self.session_uid = session_uid

    def clean_nfqueue_rules(self) -> None:
        """
        Automatically find and remove all NFQUEUE rules for the victim IP and port from the OUTPUT chain.
        """
        import re
        try:
            # List all OUTPUT rules
            result = run_command_str("iptables -S OUTPUT", capture_output=True, check=True, want_sudo=False)
            rules = result.stdout.splitlines()
            # Regex to match NFQUEUE rules for victim IP/port
            pattern = re.compile(r'-I OUTPUT -p udp(?: [^ ]*)* -d {}(?: [^ ]*)* --dport {}(?: [^ ]*)* -j NFQUEUE --queue-num (\d+)'.format(re.escape(self.victim_ip), self.victim_port))
            queue_nums = list[int]()
            for rule in rules:
                match = pattern.search(rule)
                if match:
                    qnum = int(match.group(1))
                    queue_nums.append(qnum)
            if not queue_nums:
                print_debug("No matching NFQUEUE rules found for cleaning.")
                return
            source_port = f"--sport {self.attacker_port}" if self.attacker_port != 0 else ""
            dst_ip = f"-d {self.victim_ip}" if self.victim_ip != "" else ""
            dst_port = f"--dport {self.victim_port}" if self.victim_port != 0 else ""
            for qnum in queue_nums:
                command = f"iptables -D OUTPUT -p udp {source_port} {dst_ip} {dst_port} -j NFQUEUE --queue-num {qnum}"
                print_debug(f"Cleaning NFQUEUE rule: {command}")
                try:
                    run_command_str(command, capture_output=False, check=True, want_sudo=True)
                    print_success(f"Successfully cleaned NFQUEUE rule for queue {qnum}")
                except CalledProcessError as e:
                    print_warning(f"Failed to clean NFQUEUE rule for queue {qnum}: {e}")
                except Exception as e:
                    print_error(f"Unexpected error cleaning NFQUEUE rule for queue {qnum}: {e}")
        except Exception as e:
            print_error(f"Failed to list or clean NFQUEUE rules: {e}")
    
    def stop_spoofing(self) -> bool:
        """
        Deactivate spoofing by removing iptables rules.

        Returns:
            bool: True if the rule was successfully removed, False otherwise.
        """
        if self.dry_run:
            print_info("Dry run mode: would stop spoofing and cleanup iptables rules")
            return True
            
        source_port = f"--sport {self.attacker_port}" if self.attacker_port != 0 else ""
        dst_ip = f"-d {self.victim_ip}" if self.victim_ip != "" else ""
        dst_port = f"--dport {self.victim_port}" if self.victim_port != 0 else ""

        # Unbind the spoofing function from the queue

        if self.spoofer_process is not None:
            try:
                # Terminate the whole process group (terminal + spoofer)
                p = self.spoofer_process
                print_debug(f"Terminating spoofer process with PID: {p.pid}")
                
                # Try graceful termination first
                try:
                    pgid = os.getpgid(p.pid)
                    os.killpg(pgid, SIGTERM)
                    print_debug(f"Sent SIGTERM to process group {pgid}")
                except ProcessLookupError:
                    print_debug("Process group already terminated")
                except OSError as e:
                    print_debug(f"Error getting process group ID: {e}, trying direct termination")
                    p.terminate()

                # Wait for the process to terminate gracefully
                try:
                    return_value = self.spoofer_process.wait(timeout=3)
                    if return_value != 0:
                        print_warning(f"Spoofer process terminated with non-zero exit code: {return_value}")
                    else:
                        print_success("Spoofer process terminated successfully")
                except subprocess.TimeoutExpired:
                    print_warning("Spoofer process did not terminate gracefully, forcing termination")
                    try:
                        # Force kill if graceful termination failed
                        pgid = os.getpgid(p.pid)
                        os.killpg(pgid, signal.SIGKILL)
                        p.wait(timeout=1)
                        print_success("Spoofer process force-terminated successfully")
                    except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
                        print_warning("Could not force-terminate spoofer process, it may already be dead")
                
                # Clear the process reference
                self.spoofer_process = None
                
            except Exception as e:
                print_error(f"Error terminating spoofer process: {e}")
                # Clear the process reference even if termination failed
                self.spoofer_process = None

        # Prefer removing our tagged rule in dedicated chain
        removed = False
        if self.session_uid:
            try:
                from utils.network.iptables import remove_rules_for_suid, STORMSHADOW_CHAIN
                # Try filter table first (where NFQUEUE rules go)
                removed_count = remove_rules_for_suid(self.session_uid, table="filter", chain=STORMSHADOW_CHAIN)
                if removed_count:
                    removed = True
                    print_debug(f"Removed {removed_count} NFQUEUE rules for session {self.session_uid}")
            except Exception as e:
                print_debug(f"Failed to remove rules by SUID: {e}")
        if not removed:
            # Fallback: try to remove from STORMSHADOW chain with direct command
            command = f"iptables -D STORMSHADOW -p udp {source_port} {dst_ip} {dst_port} -j NFQUEUE --queue-num {self.attack_queue_num}"
            print_debug(f"Deactivating spoofing with command: {command}")
            try:
                # Run the command to remove the iptables rule
                run_command_str(command, capture_output=False, check=True, want_sudo=True)
                print_debug(f"Successfully deactivated spoofing for packet going to {self.victim_ip}:{self.victim_port} on queue {self.attack_queue_num}")
                removed = True
            except CalledProcessError as e:
                # Last resort: try OUTPUT (legacy location)
                legacy_command = f"iptables -D OUTPUT -p udp {source_port} {dst_ip} {dst_port} -j NFQUEUE --queue-num {self.attack_queue_num}"
                try:
                    run_command_str(legacy_command, capture_output=False, check=True, want_sudo=True)
                    print_debug(f"Successfully deactivated spoofing (legacy) for packet going to {self.victim_ip}:{self.victim_port} on queue {self.attack_queue_num}")
                    removed = True
                except CalledProcessError:
                    print_debug(f"Failed to deactivate spoofing - maybe no rules existed: {e}")
            except Exception as e:
                print_error(f"An unexpected error occurred while deactivating spoofing: {e}")
        return removed

    def start_spoofing(self) -> bool:
        """
        Activate spoofing by creating iptables rules to redirect traffic.

        Args:
            receiver_ip: IP address of the receiver.
            receiver_port: Port of the receiver.
            spoofed_subnet: Subnet to be spoofed.
            src_port: Source port of the UDP flow.

        Returns:
            bool: True if the rule was successfully created, False otherwise.
        """
        
        # Check if the queue is already set
        if self.netfilter_spoofing_queue is not None:
            self.stop_spoofing()  # Stop any existing spoofing before starting a new one
            print_debug("Stopping existing spoofing before starting a new one.")

        # Install NFQUEUE rule into dedicated chain with tag/TTL via ipset if available
        suid = self.session_uid or "untagged"
        # Refresh heartbeat so cleanup won't remove it
        heartbeat_touch(suid)
        
        if self.dry_run:
            print_info("Dry run mode: would set up NFQUEUE rules and start spoofing process")
            return True
        
        set_name = ensure_nfqueue_rule_using_ipset(self.attack_queue_num, suid, anchor_chain="OUTPUT", dry_run=self.dry_run)
        if set_name:
            self._ipset_name = set_name
            # Add victim port to set (auto-TTL)
            try:
                from utils.network.iptables import ipset_add_port
                if self.victim_port:
                    ipset_add_port(set_name, self.victim_port, dry_run=self.dry_run)
            except Exception as e:
                print_warning(f"Failed adding victim port to ipset {set_name}: {e}")
        else:
            # Fallback: direct rule in dedicated chain
            if not add_nfqueue_rule_tagged(self.attack_queue_num, self.victim_port or 5060, suid, anchor_chain="OUTPUT", dry_run=self.dry_run):
                print_warning("Failed to add NFQUEUE rule (direct)")
                return False
        try:
            print_debug("Trying to start spoofer")
            print_debug("Open window: " + str(self.open_window))
            self.spoofer_process = run_python(
                module="sip_attacks.spoofer",
                args=[
                    str(self.attack_queue_num),
                    str(self.spoofed_subnet),
                    self.victim_ip,
                    str(self.victim_port),
                    str(self.attacker_port),
                    self.verbosity,  # Add verbosity argument
                ],
                want_sudo=True,
                # When escalating, preserve the current environment (venv) and allow interactive sudo
                sudo_preserve_env=True,
                sudo_non_interactive=False,
                new_terminal=False,
                open_window=self.open_window,
                window_title="SIP Spoofer",
                interactive=False,
                dry_run=self.dry_run,
                keep_window_open=False
            )

            # We wait for the spoofer to be ready
            if not self.dry_run:
                wait_ready_signal(self.attack_queue_num)
            return True
        except Exception as e:
            print_warning(f"Failed to bind spoofing function to queue {self.attack_queue_num}: {e}")
            print_info("Attempting fallback to raw socket spoofing...")
            return self._start_raw_socket_spoofing()

    def _start_raw_socket_spoofing(self) -> bool:
        """
        Start raw socket spoofing as a fallback when NFQUEUE is not available.
        
        Returns:
            bool: True if raw socket spoofing started successfully
        """
        try:
            print_info("Starting raw socket spoofing (NFQUEUE fallback)")
            self.spoofer_process = run_python(
                module="sip_attacks.raw_spoofer",
                args=[
                    str(self.attack_queue_num),
                    str(self.spoofed_subnet),
                    self.victim_ip,
                    str(self.victim_port),
                    str(self.attacker_port),
                    self.verbosity,
                ],
                want_sudo=True,
                sudo_preserve_env=True,
                sudo_non_interactive=False,
                new_terminal=False,
                open_window=self.open_window,
                window_title="SIP Raw Spoofer",
                interactive=False,
                dry_run=self.dry_run,
                keep_window_open=False
            )

            # Wait for the raw spoofer to be ready
            if not self.dry_run:
                wait_ready_signal(self.attack_queue_num)
            print_success("Raw socket spoofing started successfully")
            return True
        except Exception as e:
            print_error(f"Failed to start raw socket spoofing: {e}")
            return False
            
