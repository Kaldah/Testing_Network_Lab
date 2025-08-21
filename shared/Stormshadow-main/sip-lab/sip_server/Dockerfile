# Use the correct Asterisk base image
FROM andrius/asterisk:alpine-latest-20.5.2

RUN apk update && apk add iptables ip6tables
RUN apk add --no-cache tcpdump
RUN apk add --no-cache iptables
RUN apk add iproute2

# Copy your custom configuration and entrypoint
COPY configs/pjsip.conf /etc/asterisk/pjsip.conf
COPY configs/extensions.conf /etc/asterisk/extensions.conf
COPY entrypoint.sh /entrypoint.sh

# Make sure the entrypoint is executable
RUN chmod +x /entrypoint.sh


# Expose SIP ports
EXPOSE 5060/udp
EXPOSE 5060/tcp

ENTRYPOINT ["/entrypoint.sh"]
