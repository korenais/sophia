#!/bin/bash

# Sophia SystemD Service Setup Script
# This script sets up the systemd service for reliable Sophia bot deployment

set -e

echo "=== Sophia SystemD Service Setup ==="
echo "Timestamp: $(date)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Stop any existing service first
echo "1. Stopping any existing systemd service..."
systemctl stop sophia.service || true
systemctl disable sophia.service || true
echo ""

# Check docker compose availability
echo "2. Checking Docker Compose availability..."
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "âœ“ Docker Compose plugin found"
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    echo "âœ“ Legacy docker-compose found: $(which docker-compose)"
    COMPOSE_CMD="docker-compose"
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi
echo ""

# Create the systemd service file
echo "3. Creating systemd service..."
cat > /etc/systemd/system/sophia.service << EOF
[Unit]
Description=Sophia Bot Application Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
KillMode=none
Environment=COMPOSE_FILE=/home/aanisimov/sophia/infra/docker-compose.yml
Environment=COMPOSE_PROJECT_NAME=infra
EnvironmentFile=-/home/aanisimov/sophia/infra/.env
ExecStartPre=/usr/bin/bash -lc 'until /usr/bin/docker info >/dev/null 2>&1; do sleep 2; done'
ExecStart=/usr/bin/${COMPOSE_CMD} up -d
ExecStop=/usr/bin/${COMPOSE_CMD} down
ExecReload=/usr/bin/${COMPOSE_CMD} restart
TimeoutStartSec=300
TimeoutStopSec=60
Restart=no

[Install]
WantedBy=multi-user.target
EOF
echo "âœ“ Service file created"
echo ""

# Reload systemd and enable service
echo "4. Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable sophia.service
echo "âœ“ Service enabled for auto-start"
echo ""

# Start the service
echo "5. Starting Sophia service..."
systemctl start sophia.service
sleep 5
echo ""

# Verify service status
echo "6. Verifying service status..."
systemctl status sophia.service --no-pager -l
echo ""

# Check containers
echo "7. Checking container status..."
cd /home/aanisimov/sophia/infra
${COMPOSE_CMD} ps
echo ""

# Test connectivity
echo "8. Testing service connectivity..."
if curl -f -s http://localhost:8081 > /dev/null; then
    echo "âœ“ Frontend responding on port 8081"
else
    echo "âš  Frontend not responding on port 8081"
fi

if curl -f -s http://localhost:8055 > /dev/null; then
    echo "âœ“ API responding on port 8055"
else
    echo "âš  API not responding on port 8055"
fi
echo ""

# Check for any remaining kill events
echo "9. Checking for container kill events (should be none)..."
timeout 5s docker events --since=1m --filter container=infra_frontend_1 --format '{{.Time}} {{.Action}}' || true
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Test reboot: sudo reboot"
echo "2. After reboot, check: systemctl status sophia.service"
echo "3. Verify containers: docker compose -f /home/aanisimov/sophia/infra/docker-compose.yml ps"
echo "4. Test frontend: curl http://localhost:8081"
echo ""
echo "If issues persist, check logs: journalctl -u sophia.service -b --no-pager -n 50"
