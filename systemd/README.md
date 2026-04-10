# SystemD Service Configuration

This directory contains systemd service files and scripts for reliable Sophia bot deployment on Linux servers.

## Files

### Service Files
- **`sophia-fixed.service`** - Production-ready systemd service file

### Scripts
- **`setup_sophia_service.sh`** - Automated service setup script

## Quick Setup

### Automated Setup (Recommended)
```bash
# Run as root
sudo chmod +x setup_sophia_service.sh
sudo ./setup_sophia_service.sh
```

### Manual Setup
```bash
# Copy the fixed service file
sudo cp sophia-fixed.service /etc/systemd/system/sophia.service

# Reload systemd and enable
sudo systemctl daemon-reload
sudo systemctl enable sophia.service
sudo systemctl start sophia.service

# Verify
systemctl status sophia.service
```

## Troubleshooting

### Common Issues Fixed

1. **CHDIR Errors**: Fixed by using absolute paths instead of WorkingDirectory
2. **Docker Compose Path**: Auto-detects docker-compose vs docker compose
3. **Restart Loops**: Disabled with `Restart=no` and `KillMode=none`
4. **Container Kills**: Prevented with proper systemd configuration

### Service Status
```bash
# Check service status
systemctl status sophia.service --no-pager -l

# Check containers
docker-compose -f /home/aanisimov/sophia/infra/docker-compose.yml ps

# Test connectivity
curl http://localhost:8081
curl http://localhost:8055
```

## Benefits

- ✅ **Auto-start after reboots**
- ✅ **Proper dependency management** (waits for Docker)
- ✅ **No container kill/restart loops**
- ✅ **Reliable service management**
- ✅ **Production-ready configuration**

## Configuration

The service automatically:
- Waits for Docker to be ready
- Uses absolute paths (no CHDIR issues)
- Detects docker-compose vs docker compose
- Sets proper environment variables
- Manages container lifecycle correctly

## Paths

- **Service File**: `/etc/systemd/system/sophia.service`
- **Working Directory**: `/home/aanisimov/sophia/infra/`
- **Compose File**: `/home/aanisimov/sophia/infra/docker-compose.yml`
- **Environment**: `/home/aanisimov/sophia/infra/.env`
