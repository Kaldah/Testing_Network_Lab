
import os
import time
import uuid
import subprocess
from typing import List, Optional, Tuple

from utils.core.logs import print_debug, print_info, print_warning
from utils.core.command_runner import run_command_str

def get_current_iptables_queue_num() -> int:
    """
    Get the current number of packets in the iptables queue.
    """
    # run the iptables list command and filter in Python. Do NOT include a shell pipe
    # in the command string because run_command_str uses shlex.split + subprocess.run
    # without a shell. Passing '|' and 'grep' as arguments results in iptables being
    # invoked with invalid arguments (see CalledProcessError with exit status 2).
    # Note: This is a read-only operation, so dry_run is not used
    command = "iptables -S"
    try:
        print_debug(f"Running command to check current queue number: {command}")
        result = run_command_str(command, capture_output=True, check=True, want_sudo=True)
        # Filter for NFQUEUE lines using Python instead of a shell pipeline
        lines = [l for l in result.stdout.strip().split('\n') if 'NFQUEUE' in l]
        if not lines:
            print_debug("No NFQUEUE rules found in iptables. Assuming queue number is -1 for none.")
            return -1
        return max(int(line.split('--queue-num ')[1]) for line in lines if '--queue-num ' in line)
    except subprocess.CalledProcessError as e:
        # Show the error returned by the subprocess (returncode / stderr) to help debugging
        print_warning(f"Failed to get current queue number: {e} (returncode={getattr(e, 'returncode', None)})")
    except IndexError:
        print_debug("No NFQUEUE rules found in iptables. Assuming queue number is -1 for none.")
    return -1  # Default to -1 if no rules found or an error occurs

def create_matching_queue(queue_num: int, chain: str, dst_port: int, dry_run: bool = False) -> bool:
    """
    Match the queue number to a specific iptables rule.

    Args:
        queue_num (int): The queue number to match.
        chain (str): The iptables chain to apply the rule to.
        dst_port (int): The destination port to match.
        dry_run (bool): If True, don't actually execute the command.
    Returns:
        bool: True if successful, False otherwise.
    """
    command = f"sudo iptables -I {chain} -p udp --dport {dst_port} -j NFQUEUE --queue-num {queue_num}"
    try:
        print_debug(f"Creating matching queue with command: {command}")
        run_command_str(command, capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to create matching queue: {e}")
        return False
    except Exception as e:
        print_warning(f"An unexpected error occurred while creating matching queue: {e}")
        return False
    print_debug(f"Successfully created matching queue {queue_num} for chain {chain} on port {dst_port}")
    return True

# --------------------------------------------------------------------------------------
# Stormshadow rule management (chains, tagging, cleanup, and optional ipset support)
# --------------------------------------------------------------------------------------

STORMSHADOW_CHAIN = "STORMSHADOW"
STORMSHADOW_NAT_CHAIN = "STORMSHADOW-NAT"
COMMENT_PREFIX = "Stormshadow"  # comment tag prefix used to identify rules
DEFAULT_TTL_SECONDS = 2 * 60 * 60  # 2 hours
DEFAULT_HEARTBEAT_DIR = "/run/stormshadow"  # volatile; survives only until reboot


def generate_suid() -> str:
    """Generate a session unique ID for tagging rules."""
    return uuid.uuid4().hex[:10]


def _now() -> int:
    return int(time.time())


def _ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print_warning(f"Failed to create directory {path}: {e}")


def heartbeat_touch(suid: str, heartbeat_dir: str = DEFAULT_HEARTBEAT_DIR) -> str:
    """
    Update a heartbeat file for the given SUID. Cleanup logic will consider
    fresh heartbeats as active sessions and avoid removing their rules.
    Returns the heartbeat file path.
    """
    _ensure_dir(heartbeat_dir)
    hb_path = os.path.join(heartbeat_dir, f"{suid}.hb")
    try:
        with open(hb_path, "a", encoding="utf-8"):
            pass
        os.utime(hb_path, None)
        print_debug(f"Heartbeat touched: {hb_path}")
    except Exception as e:
        print_warning(f"Failed to touch heartbeat file {hb_path}: {e}")
    return hb_path


def heartbeat_remove(suid: str, heartbeat_dir: str = DEFAULT_HEARTBEAT_DIR) -> bool:
    """
    Remove a heartbeat file for the given SUID. This should be called during
    application shutdown to ensure proper cleanup of rules.
    Returns True if file was removed or didn't exist, False on error.
    """
    hb_path = os.path.join(heartbeat_dir, f"{suid}.hb")
    try:
        os.unlink(hb_path)
        print_debug(f"Heartbeat file removed: {hb_path}")
        return True
    except FileNotFoundError:
        print_debug(f"Heartbeat file already removed: {hb_path}")
        return True
    except Exception as e:
        print_warning(f"Failed to remove heartbeat file {hb_path}: {e}")
        return False


def _comment_for(suid: str, created_ts: Optional[int] = None, extra: Optional[str] = None, preserve: bool = False) -> str:
    """
    Build a consistent comment string to tag iptables rules so we can detect and cleanup later.
    Format: "Stormshadow:{suid}:{created_ts}[:{extra}][:{NOT_DELETE}]"
    
    Args:
        suid: Session unique identifier
        created_ts: Creation timestamp (defaults to current time)
        extra: Extra information to include in comment
        preserve: If True, adds NOT_DELETE tag to preserve rule during cleanup
    """
    if created_ts is None:
        created_ts = _now()
    parts = [COMMENT_PREFIX, suid, str(created_ts)]
    if extra:
        parts.append(str(extra))
    if preserve:
        parts.append("NOT_DELETE")
    return ":".join(parts)


def _parse_comment(comment: str) -> Optional[Tuple[str, int, Optional[str], bool]]:
    """
    Parse our comment format; return (suid, created_ts, extra, preserve) or None if not ours.
    
    Args:
        comment: The comment string to parse
        
    Returns:
        Tuple containing (suid, created_ts, extra, preserve) or None if not a Stormshadow comment
    """
    if not comment or COMMENT_PREFIX not in comment:
        return None
    try:
        # Accept either Stormshadow:... or /* Stormshadow:... */ rendered forms
        raw = comment.strip().strip("/*").strip("*/").strip()
        if not raw.startswith(COMMENT_PREFIX + ":"):
            return None
        parts = raw.split(":")
        if len(parts) < 3:
            return None
        
        _, suid, ts = parts[0], parts[1], parts[2]
        created_ts = int(ts)
        
        # Handle extra and preserve flag
        extra = None
        preserve = False
        
        if len(parts) > 3:
            remaining_parts = parts[3:]
            # Check if last part is NOT_DELETE
            if remaining_parts and remaining_parts[-1] == "NOT_DELETE":
                preserve = True
                remaining_parts = remaining_parts[:-1]
            
            # Join remaining parts as extra (in case extra contained colons)
            if remaining_parts:
                extra = ":".join(remaining_parts)
        
        return suid, created_ts, extra, preserve
    except Exception:
        return None


def _iptables_S(chain: Optional[str] = None, table: Optional[str] = None) -> List[str]:
    """Return iptables -S output lines, optionally for a specific chain and table (default filter).
    This is a read-only operation, so dry_run is not used."""
    base = "iptables -S"
    if table:
        base = f"iptables -t {table} -S"
    if chain:
        base = f"{base} {chain}"
    try:
        print_debug(f"Listing iptables rules: {base}")
        res = run_command_str(base, capture_output=True, check=True, want_sudo=True)
        return [l for l in res.stdout.splitlines() if l.strip()]
    except subprocess.CalledProcessError as e:
        # Chain may not exist yet, that's OK for cleanup
        if chain and ("No chain/target/match" in str(e) or "does not exist" in str(e)):
            print_debug(f"Chain {chain} in table {table or 'filter'} does not exist yet")
            return []
        print_warning(f"Failed to list iptables rules: {e}")
        return []


def ensure_chain_and_anchor(anchor_chain: str = "INPUT", table: str = "filter", suid: str = "anchor", preserve: bool = False, dry_run: bool = False) -> None:
    """
    Ensure a dedicated STORMSHADOW chain exists and that there's a jump from the given anchor_chain.
    This keeps Stormshadow rules isolated and easy to cleanup.
    
    Args:
        anchor_chain: The chain to jump from (INPUT, OUTPUT, etc.)
        table: The iptables table (filter, nat, etc.)
        suid: Session unique identifier for tagging
        preserve: If True, marks rules with NOT_DELETE to preserve during cleanup
        dry_run: If True, don't actually execute modification commands
    """
    # 1) Create chain if missing
    try:
        run_command_str(
            f"iptables -t {table} -N {STORMSHADOW_CHAIN}",
            capture_output=False,
            check=True,
            want_sudo=True,
            dry_run=dry_run
        )
        print_debug(f"Created chain {STORMSHADOW_CHAIN} in table {table}")
    except subprocess.CalledProcessError:
        # Chain probably exists; that's fine
        pass

    # 2) Ensure anchor jump exists (check is read-only, so no dry_run)
    try:
        run_command_str(
            f"iptables -t {table} -C {anchor_chain} -j {STORMSHADOW_CHAIN}",
            capture_output=False,
            check=True,
            want_sudo=True,
        )
        print_debug(f"Anchor jump already present: {anchor_chain} -> {STORMSHADOW_CHAIN}")
    except subprocess.CalledProcessError:
        # Not present; insert at top for early processing
        comment = _comment_for(suid, extra=f"{anchor_chain}->{STORMSHADOW_CHAIN}", preserve=preserve)
        try:
            run_command_str(
                f"iptables -t {table} -I {anchor_chain} 1 -j {STORMSHADOW_CHAIN} -m comment --comment '{comment}'",
                capture_output=False,
                check=True,
                want_sudo=True,
                dry_run=dry_run
            )
            print_debug(f"Inserted anchor jump: {anchor_chain} -> {STORMSHADOW_CHAIN}")
        except subprocess.CalledProcessError as e:
            print_warning(f"Failed to insert anchor jump to {STORMSHADOW_CHAIN}: {e}")


def ensure_nat_chain_and_anchor(anchor_chain: str = "OUTPUT", suid: str = "anchor", preserve: bool = False, dry_run: bool = False) -> None:
    """
    Same as ensure_chain_and_anchor but for the nat table, defaulting to OUTPUT chain.
    
    Args:
        anchor_chain: The chain to jump from (OUTPUT, PREROUTING, etc.)
        suid: Session unique identifier for tagging
        preserve: If True, marks rules with NOT_DELETE to preserve during cleanup
        dry_run: If True, don't actually execute modification commands
    """
    table = "nat"
    try:
        run_command_str(
            f"iptables -t {table} -N {STORMSHADOW_NAT_CHAIN}",
            capture_output=False,
            check=True,
            want_sudo=True,
            dry_run=dry_run
        )
        print_debug(f"Created chain {STORMSHADOW_NAT_CHAIN} in table {table}")
    except subprocess.CalledProcessError:
        pass

    # Check is read-only, so no dry_run
    try:
        run_command_str(
            f"iptables -t {table} -C {anchor_chain} -j {STORMSHADOW_NAT_CHAIN}",
            capture_output=False,
            check=True,
            want_sudo=True,
        )
        print_debug(f"Anchor jump already present: {anchor_chain} -> {STORMSHADOW_NAT_CHAIN}")
    except subprocess.CalledProcessError:
        comment = _comment_for(suid, extra=f"{anchor_chain}->{STORMSHADOW_NAT_CHAIN}", preserve=preserve)
        try:
            run_command_str(
                f"iptables -t {table} -I {anchor_chain} 1 -j {STORMSHADOW_NAT_CHAIN} -m comment --comment '{comment}'",
                capture_output=False,
                check=True,
                want_sudo=True,
                dry_run=dry_run
            )
            print_debug(f"Inserted anchor jump: {anchor_chain} -> {STORMSHADOW_NAT_CHAIN}")
        except subprocess.CalledProcessError as e:
            print_warning(f"Failed to insert nat anchor jump to {STORMSHADOW_NAT_CHAIN}: {e}")


def add_nfqueue_rule_tagged(queue_num: int, dst_port: int, suid: str, anchor_chain: str = "INPUT", preserve: bool = False, dry_run: bool = False) -> bool:
    """
    Add an NFQUEUE rule for a UDP destination port into the dedicated STORMSHADOW chain
    and tag it with a Stormshadow comment carrying the SUID and creation timestamp.
    
    Args:
        queue_num: NFQUEUE queue number
        dst_port: UDP destination port
        suid: Session unique identifier
        anchor_chain: Chain to jump from (INPUT, OUTPUT, etc.)
        preserve: If True, marks rule with NOT_DELETE to preserve during cleanup
        dry_run: If True, don't actually execute modification commands
    """
    ensure_chain_and_anchor(anchor_chain=anchor_chain, table="filter", suid=suid, preserve=preserve, dry_run=dry_run)
    comment = _comment_for(suid, extra=f"udp_dport={dst_port};queue={queue_num}", preserve=preserve)
    command = (
        f"iptables -I {STORMSHADOW_CHAIN} -p udp --dport {dst_port} "
        f"-j NFQUEUE --queue-num {queue_num} -m comment --comment '{comment}'"
    )
    try:
        print_debug(f"Adding tagged NFQUEUE rule: {command}")
        run_command_str(command, capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
        return True
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to add tagged NFQUEUE rule: {e}")
        return False


def remove_rules_for_suid(suid: str, table: str = "filter", chain: str = STORMSHADOW_CHAIN, dry_run: bool = False) -> int:
    """Remove all rules in given table/chain that have a Stormshadow comment with the given SUID. Returns removed count."""
    removed = 0
    lines = _iptables_S(chain=chain, table=table)
    # Delete using full spec: replace leading '-A' with '-D'
    for line in lines:
        if "-m comment --comment" in line and COMMENT_PREFIX in line and suid in line:
            delete = line.replace("-A", "-D", 1)
            try:
                run_command_str(
                    f"iptables -t {table} {delete}", capture_output=False, check=True, want_sudo=True, dry_run=dry_run
                )
                removed += 1
                print_debug(f"Removed rule for SUID {suid}: iptables -t {table} {delete}")
            except subprocess.CalledProcessError as e:
                print_warning(f"Failed to remove rule: iptables -t {table} {delete} -> {e}")
    return removed

def remove_all_rules_for_suid(suid: str, dry_run: bool = False) -> int:
    """
    Remove ALL rules for a given SUID across all tables and chains, including anchor jumps.
    This is used during application shutdown to ensure complete cleanup.
    Returns total number of rules removed.
    """
    removed_total = 0
    
    # Remove anchor jumps in main chains (filter table)
    for anchor_chain in ["INPUT", "OUTPUT", "FORWARD"]:
        lines = _iptables_S(chain=anchor_chain, table="filter")
        for line in lines:
            if f"-j {STORMSHADOW_CHAIN}" in line and "-m comment --comment" in line and COMMENT_PREFIX in line and suid in line:
                delete_rule = line.replace("-A", "-D", 1)
                try:
                    run_command_str(f"iptables -t filter {delete_rule}", capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
                    removed_total += 1
                    print_debug(f"Removed anchor jump for SUID {suid}: {delete_rule}")
                except subprocess.CalledProcessError as e:
                    print_warning(f"Failed to remove anchor jump: {e}")
    
    # Remove anchor jumps in main chains (nat table)  
    for anchor_chain in ["OUTPUT", "PREROUTING", "POSTROUTING"]:
        lines = _iptables_S(chain=anchor_chain, table="nat")
        for line in lines:
            if f"-j {STORMSHADOW_NAT_CHAIN}" in line and "-m comment --comment" in line and COMMENT_PREFIX in line and suid in line:
                delete_rule = line.replace("-A", "-D", 1)
                try:
                    run_command_str(f"iptables -t nat {delete_rule}", capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
                    removed_total += 1
                    print_debug(f"Removed nat anchor jump for SUID {suid}: {delete_rule}")
                except subprocess.CalledProcessError as e:
                    print_warning(f"Failed to remove nat anchor jump: {e}")
    
    # Remove rules in STORMSHADOW chains
    removed_total += remove_rules_for_suid(suid, table="filter", chain=STORMSHADOW_CHAIN, dry_run=dry_run)
    removed_total += remove_rules_for_suid(suid, table="nat", chain=STORMSHADOW_NAT_CHAIN, dry_run=dry_run)

    return removed_total


def cleanup_stale_heartbeats(ttl_seconds: int = DEFAULT_TTL_SECONDS, heartbeat_dir: str = DEFAULT_HEARTBEAT_DIR, dry_run: bool = False) -> int:
    """
    Remove stale heartbeat files (older than ttl_seconds).
    This should be called before cleanup_stale_rules to ensure proper cleanup.
    Returns number of heartbeat files removed.
    """
    removed_count = 0
    now = _now()

    if dry_run:
        print_info(f"Dry run: would remove stale heartbeat files in {heartbeat_dir}")
        return 0

    try:
        if not os.path.exists(heartbeat_dir):
            return 0
            
        for filename in os.listdir(heartbeat_dir):
            if not filename.endswith('.hb'):
                continue
                
            hb_path = os.path.join(heartbeat_dir, filename)
            try:
                st = os.stat(hb_path)
                age = now - int(st.st_mtime)
                if age >= ttl_seconds:
                    os.unlink(hb_path)
                    removed_count += 1
                    print_debug(f"Removed stale heartbeat file: {hb_path}")

            except (FileNotFoundError, OSError) as e:
                # File might have been removed by another process
                print_debug(f"Could not process heartbeat file {hb_path}: {e}")
                
    except Exception as e:
        print_warning(f"Error during heartbeat cleanup: {e}")
        
    return removed_count


def cleanup_stale_rules(ttl_seconds: int = DEFAULT_TTL_SECONDS, heartbeat_dir: str = DEFAULT_HEARTBEAT_DIR, dry_run: bool = False) -> int:
    """
    Remove Stormshadow-tagged rules from our dedicated chains if they appear stale.
    A rule is considered stale if its embedded timestamp is older than ttl_seconds and
    there's no recent heartbeat file for its SUID (mtime > now - ttl_seconds/2).
    
    First cleans up stale heartbeat files, then removes corresponding rules.
    Returns number of rules removed.
    """
    # First cleanup stale heartbeat files
    removed_hb = cleanup_stale_heartbeats(ttl_seconds, heartbeat_dir, dry_run=dry_run)
    if removed_hb > 0:
        print_debug(f"Removed {removed_hb} stale heartbeat files during startup cleanup")
    
    now = _now()
    half_ttl = max(60, ttl_seconds // 2)
    removed_total = 0

    def should_remove(comment_text: str) -> Optional[str]:
        parsed = _parse_comment(comment_text)
        if not parsed:
            return None
        suid, created_ts, _extra, preserve = parsed
        
        # Never remove rules marked with NOT_DELETE
        if preserve:
            return None
            
        age = now - created_ts
        hb_path = os.path.join(heartbeat_dir, f"{suid}.hb")
        hb_fresh = False
        try:
            st = os.stat(hb_path)
            hb_fresh = (now - int(st.st_mtime)) < half_ttl
        except FileNotFoundError:
            hb_fresh = False
        
        # Remove if no fresh heartbeat OR if rule is older than TTL (safety fallback)
        if not hb_fresh or age >= ttl_seconds:
            return suid
        return None

    # Clean up anchor jumps in various chains (INPUT, OUTPUT, etc.)
    for anchor_chain in ["INPUT", "OUTPUT", "FORWARD"]:
        anchor_lines = _iptables_S(chain=anchor_chain, table="filter")
        for line in anchor_lines:
            if f"-j {STORMSHADOW_CHAIN}" in line and "-m comment --comment" in line and COMMENT_PREFIX in line:
                try:
                    # Extract comment content between quotes
                    import re
                    comment_match = re.search(r'--comment\s+"([^"]+)"', line)
                    if comment_match:
                        comment_text = comment_match.group(1)
                        candidate = should_remove(comment_text)
                        if candidate:
                            # Remove this specific anchor jump
                            delete_rule = line.replace("-A", "-D", 1)
                            try:
                                run_command_str(f"iptables -t filter {delete_rule}", capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
                                removed_total += 1
                                print_debug(f"Removed stale anchor jump: {delete_rule}")
                            except subprocess.CalledProcessError as e:
                                print_warning(f"Failed to remove stale anchor jump: {e}")
                except Exception as e:
                    print_warning(f"Error processing anchor jump line: {e}")

    # filter/STORMSHADOW
    for line in _iptables_S(chain=STORMSHADOW_CHAIN, table="filter"):
        if "-m comment --comment" in line and COMMENT_PREFIX in line:
            # Extract the comment content between quotes
            try:
                comment_text = line.split("--comment", 1)[1].strip().split(" ", 1)[1].strip().strip("'\"")
            except Exception:
                comment_text = line
            candidate = should_remove(comment_text)
            if candidate:
                removed_total += remove_rules_for_suid(candidate, table="filter", chain=STORMSHADOW_CHAIN, dry_run=dry_run)

    # nat/STORMSHADOW-NAT
    for line in _iptables_S(chain=STORMSHADOW_NAT_CHAIN, table="nat"):
        if "-m comment --comment" in line and COMMENT_PREFIX in line:
            try:
                comment_text = line.split("--comment", 1)[1].strip().split(" ", 1)[1].strip().strip("'\"")
            except Exception:
                comment_text = line
            candidate = should_remove(comment_text)
            if candidate:
                removed_total += remove_rules_for_suid(candidate, table="nat", chain=STORMSHADOW_NAT_CHAIN, dry_run=dry_run)

    return removed_total


def has_ipset() -> bool:
    """Return True if ipset command is available. This is a read-only check, so dry_run is not used."""
    try:
        run_command_str("ipset --version", capture_output=True, check=True, want_sudo=True)
        return True
    except Exception:
        return False


def ensure_ipset_set(name: str, set_type: str = "bitmap:port", timeout: int = DEFAULT_TTL_SECONDS, dry_run: bool = False) -> bool:
    """Create an ipset set if missing. bitmap:port with timeout provides auto-expiry for ports."""
    # Check if exists (read-only, no dry_run)
    try:
        run_command_str(f"ipset list {name}", capture_output=False, check=True, want_sudo=True)
        return True  # exists
    except subprocess.CalledProcessError:
        pass
    
    # Create the set (modifies, uses dry_run)
    try:
        run_command_str(
            f"ipset create {name} {set_type} timeout {timeout}", 
            capture_output=False, 
            check=True, 
            want_sudo=True,
            dry_run=dry_run
        )
        print_debug(f"Created ipset {name} ({set_type}) with timeout {timeout}s")
        return True
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to create ipset {name}: {e}")
        return False


def ipset_add_port(name: str, port: int, timeout: int = DEFAULT_TTL_SECONDS, dry_run: bool = False) -> bool:
    """Add or refresh a port in the ipset with a timeout (auto-expires)."""
    try:
        run_command_str(
            f"ipset add {name} {port} timeout {timeout} -exist", 
            capture_output=False, 
            check=True, 
            want_sudo=True,
            dry_run=dry_run
        )
        return True
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to add port {port} to ipset {name}: {e}")
        return False


def ensure_nfqueue_rule_using_ipset(queue_num: int, suid: str, anchor_chain: str = "INPUT", set_timeout: int = DEFAULT_TTL_SECONDS, dry_run: bool = False) -> Optional[str]:
    """
        Better approach: use ipset to control which ports are sent to NFQUEUE, with per-port TTL.

        - Create ipset set name "stormshadow_ports_{suid}" (bitmap:port, timeout).
        - Insert a single iptables rule in STORMSHADOW chain matching
            "-m set --match-set <set> dst" and sending to NFQUEUE.
        - Entries (ports) in the set expire automatically.

        Returns the set name if successful, else None.
    """
    if not has_ipset():
        print_warning("ipset not available; falling back to direct iptables rules.")
        return None
    
    ensure_chain_and_anchor(anchor_chain=anchor_chain, table="filter", suid=suid, preserve=False, dry_run=dry_run)
    set_name = f"stormshadow_ports_{suid}"
    
    if not ensure_ipset_set(set_name, set_type="bitmap:port", timeout=set_timeout, dry_run=dry_run):
        return None
    
    # Ensure the single NFQUEUE rule exists (check is read-only, no dry_run)
    check_cmd = (
        f"iptables -C {STORMSHADOW_CHAIN} -p udp -m set --match-set {set_name} dst "
        f"-j NFQUEUE --queue-num {queue_num}"
    )
    try:
        run_command_str(check_cmd, capture_output=False, check=True, want_sudo=True)
        print_debug("ipset-backed NFQUEUE rule already present")
        return set_name
    except subprocess.CalledProcessError:
        pass

    comment = _comment_for(suid, extra=f"ipset={set_name};queue={queue_num}")
    add_cmd = (
        f"iptables -I {STORMSHADOW_CHAIN} -p udp -m set --match-set {set_name} dst "
        f"-j NFQUEUE --queue-num {queue_num} -m comment --comment '{comment}'"
    )
    try:
        run_command_str(add_cmd, capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
        print_debug("Inserted ipset-backed NFQUEUE rule")
        return set_name
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to add ipset-backed NFQUEUE rule: {e}")
        return None


def ipset_destroy(name: str, dry_run: bool = False) -> None:
    try:
        run_command_str(f"ipset destroy {name}", capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
    except subprocess.CalledProcessError:
        pass

def activate_return_path(
    receiver_ip: str,
    receiver_port: int,
    spoofed_subnet: str,
    src_port: int = 0,
    suid: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """
    Activate the return path for a specific UDP flow by modifying iptables rules.

    Args:
        receiver_ip: Destination IP address of the UDP flow.
        receiver_port: Acknowledgment port for the UDP flow.
        spoofed_subnet: Spoofed subnet to use for the return path.
        src_port: Source port of the UDP flow.
        suid: Session unique identifier
        dry_run: If True, don't actually execute modification commands
    """
    source_port = ""
    if src_port != 0:
        source_port = f"--sport {src_port}"
    else:
        print_warning("No source port specified, all udp packets will be affected.")
    try:
        ensure_nat_chain_and_anchor(anchor_chain="OUTPUT", suid=suid or "anchor", preserve=False, dry_run=dry_run)
        comment = _comment_for(suid, extra=f"dnat_to={receiver_ip}:{receiver_port}") if suid else None
        base = (
            f"sudo iptables -t nat -I {STORMSHADOW_NAT_CHAIN} -p udp {source_port} -d {spoofed_subnet} "
            f"-j DNAT --to-destination {receiver_ip}:{receiver_port}"
        )
        command = f"{base} -m comment --comment '{comment}'" if comment else base
        print_debug(f"Activating return path with command: {command}")
        run_command_str(command, capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to activate return path: {e}")
    
def deactivate_return_path(
    receiver_ip: str,
    receiver_port: int,
    spoofed_subnet: str,
    src_port: int = 0,
    suid: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """
    Deactivate the return path for a specific UDP flow by removing iptables rules.

    Args:
        receiver_ip: Destination IP address of the UDP flow.
        receiver_port: Acknowledgment port for the UDP flow.
        spoofed_subnet: Spoofed subnet to use for the return path.
        src_port: Source port of the UDP flow.
        suid: Session unique identifier
        dry_run: If True, don't actually execute modification commands

    Returns:
        bool: True if the rule was successfully removed, False otherwise.
    """
    source_port = ""
    if src_port != 0:
        source_port = f"--sport {src_port}"
    else:
        print_warning("No source port specified, all udp packets will be affected.")
    try:
        # Try delete with our chain and with comment (if any)
        base = (
            f"sudo iptables -t nat -D {STORMSHADOW_NAT_CHAIN} -p udp {source_port} -d {spoofed_subnet} "
            f"-j DNAT --to-destination {receiver_ip}:{receiver_port}"
        )
        if suid:
            comment = _comment_for(suid, extra=f"dnat_to={receiver_ip}:{receiver_port}")
            cmd = f"{base} -m comment --comment '{comment}'"
            print_debug(f"Deactivating return path (tagged) with command: {cmd}")
            run_command_str(cmd, capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
            return True
        # Fallback: try without comment in our chain
        print_debug(f"Deactivating return path (untagged) with command: {base}")
        run_command_str(base, capture_output=False, check=True, want_sudo=True, dry_run=dry_run)
        return True
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to deactivate return path: {e}")
        return False
    
