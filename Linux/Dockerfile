# syntax=docker/dockerfile:1.6

############################################
# 1) Build stage: compile wheels & tools
############################################
ARG PYTHON_TAG=3.13-slim
FROM python:${PYTHON_TAG} AS builder
ENV DEBIAN_FRONTEND=noninteractive

# Build deps for C extensions + headers for NetfilterQueue, Scapy extras
# Include python3-dev so extension modules can find Python headers when building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential gcc make pkg-config git ca-certificates curl \
  python3-dev linux-libc-dev \
  libnetfilter-queue-dev libnfnetlink-dev libmnl-dev \
  libpcap-dev libnet1-dev \
 && rm -rf /var/lib/apt/lists/*

# Isolated venv to keep the final image small/clean
ENV VENV=/opt/venv
RUN python -m venv "$VENV"
ENV PATH="$VENV/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ---- Runtime Python deps (from your pyproject) ----
RUN printf '%s\n' \
  'fastapi>=0.116.1' \
  'ifaddr>=0.2.0' \
  'netfilterqueue>=1.1.0' \
  'netifaces>=0.11.0' \
  'netifaces2>=0.0.22' \
  'pyyaml>=6.0.2' \
  'scapy>=2.6.1' \
  'uvicorn>=0.35.0' \
  'colorama>=0.4.6' \
  'typing-extensions>=4.5.0' \
  > /tmp/requirements.txt \
 && pip install --no-cache-dir -r /tmp/requirements.txt

############################################
# 2) Final runtime: minimal
############################################
FROM kalilinux/kali-rolling
ENV DEBIAN_FRONTEND=noninteractive

# Runtime libs + iptables tools for NFQUEUE rules + Tk + build tools for additional packages
# Minimal runtime packages: keep only what's needed for StormShadow and basic networking
# - runtime libs for netfilterqueue/scapy
# - basic network tools: iproute2, iptables, tcpdump, net-tools, ping
# - small set of utilities: curl, wget, netcat, nmap, openssh-client, socat
# - keep build-essential so users can still pip-install packages that need compilation

RUN apt-get update && apt-get install -y --no-install-recommends \
  iptables iproute2 tcpdump \
  libnetfilter-queue1 libnfnetlink0 libmnl0 libpcap0.8 libnet1 \
  build-essential gcc make pkg-config \
  libnetfilter-queue-dev libnfnetlink-dev libmnl-dev linux-libc-dev \
  libpcap-dev libnet1-dev python3-dev \
  curl wget net-tools iputils-ping netcat-traditional nmap \
  openssh-client socat \
  python3 python3-pip python3-tk python3-venv \
 && rm -rf /var/lib/apt/lists/*

# Bring venv
ENV VENV=/opt/venv
COPY --from=builder $VENV $VENV
# Fix venv symlinks to point to the correct python location
RUN ln -sf /usr/bin/python3 $VENV/bin/python && \
    ln -sf /usr/bin/python3 $VENV/bin/python3 && \
    ln -sf /usr/bin/python3 $VENV/bin/python3.13
ENV PATH="$VENV/bin:${PATH}"

# Mount your project at /app when running
WORKDIR /app

# Provide a simple entrypoint to isolate iptables rules and print tips
COPY Linux/entrypoint.sh /usr/local/bin/attacker-entrypoint.sh
RUN chmod +x /usr/local/bin/attacker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/attacker-entrypoint.sh"]
CMD ["/bin/bash"]
