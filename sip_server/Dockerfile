# Use the correct Asterisk base image
FROM andrius/asterisk:alpine-latest-20.5.2

RUN apk update && \
	apk add --no-cache \
		iptables ip6tables iproute2 tcpdump \
		nmap netcat-openbsd curl wget bind-tools \
		net-tools bridge-utils ethtool traceroute \
		mtr fping hping3 arping ngrep \
		openssh-client socat nc-traditional \
		wireshark-common tcpflow scapy || true && \
	# Try installing optional/extra packages; don't fail the build if unavailable
	apk add --no-cache aircrack-ng masscan hydra nikto dirb sqlmap hashcat \
		sshpass cifs-utils nfs-utils dnsutils whois macchanger || true

# Copy entrypoint (configs are bind-mounted via docker-compose)
COPY sip_server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose SIP ports (internal only unless mapped)
EXPOSE 5060/udp 5060/tcp

ENTRYPOINT ["/entrypoint.sh"]
