# SendTraffic - Network Traffic Generator & Domain Blocker Verifier

A Python script that generates network traffic using iperf3, downloads test files, sends dummy traffic, and verifies domain blocking status. Designed to run as a long-term background process with automatic port rotation.

## Features

- **iperf3 Server/Client Mode**: Generate network traffic at 1 Mbps with automatic port rotation
- **Periodic Tasks**: Download test files every interval (default: 10 minutes)
- **Dummy Traffic**: Send 1-second bursts of traffic to test ports
- **Domain Blocking Verification**: Curl popular domains and verify they are blocked
- **Auto Port Discovery**: Server and client automatically sync port changes via discovery service
- **Runs Indefinitely**: Long-running process suitable for continuous testing

## Requirements

- Python 3.6+
- `iperf3` (installed and in system PATH)
- `curl` (installed and in system PATH)
- Root/Administrator privileges for network operations

## Installation

### Linux/macOS

```bash
# Install iperf3 and curl
sudo apt-get install iperf3 curl          # Debian/Ubuntu
brew install iperf3 curl                  # macOS

# Make script executable
chmod +x sendtraffic.py
```

### Windows

```bash
# Install iperf3 and curl using package managers
# Or download from: https://iperf.fr/iperf-download.php
# And: https://curl.se/download.html

# Run with Python
python sendtraffic.py --mode server --port 5201
```

## Usage

### Basic Server Mode

```bash
sudo python3 sendtraffic.py --mode server --port 5201 --background
```

**Output:**
```
[2026-06-11 12:00:00] Starting iperf3 server (base port 5201, running indefinitely)
[2026-06-11 12:00:00] ✓ Discovery service listening on port 9999
[2026-06-11 12:00:00] Starting periodic background tasks (every 600 seconds)
[2026-06-11 12:00:00] ▶ iperf3 server listening on port 5201 (discovery advertising this port)
[2026-06-11 12:00:30] ⊘ Port 5201 timeout reached, incrementing to next port
[2026-06-11 12:00:31] ▶ iperf3 server listening on port 5202 (discovery advertising this port)
```

### Basic Client Mode

```bash
sudo python3 sendtraffic.py --mode client --host 192.168.1.100 --background
```

**Output:**
```
[2026-06-11 12:00:00] Starting iperf3 client connecting to 192.168.1.100 at 1 Mbps
[2026-06-11 12:00:00] Starting periodic background tasks (every 600 seconds)
[2026-06-11 12:00:01] Querying discovery service at 192.168.1.100:9999...
[2026-06-11 12:00:01] ✓ Discovery returned port: 5201
[2026-06-11 12:00:01] ▶ iperf3 client connecting to 192.168.1.100:5201
```

## Command-Line Arguments

```
positional arguments:
  --mode {server,client}     iperf3 mode: server or client (required)

optional arguments:
  --port PORT               Base port for iperf3 (default: 5201)
  --max-port PORT           Maximum port before cycling back to base port (optional)
  --host HOST               Server host for client mode (default: 127.0.0.1)
  --interval INTERVAL       Interval in seconds for periodic tasks (default: 600 = 10 minutes)
  --port-duration DURATION  Duration in seconds each port is used before incrementing (default: 30)
  --background              Run periodic tasks in background
```

## Examples

### Scenario 1: Local Testing (Same Machine)

**Terminal 1 - Server:**
```bash
sudo python3 sendtraffic.py --mode server --port 5201 --background
```

**Terminal 2 - Client:**
```bash
sudo python3 sendtraffic.py --mode client --host 127.0.0.1 --background
```

### Scenario 2: Remote Testing (Separate Machines)

**Server Machine (192.168.1.100):**
```bash
sudo python3 sendtraffic.py --mode server --port 5201 --port-duration 60 --background
```

**Client Machine:**
```bash
sudo python3 sendtraffic.py --mode client --host 192.168.1.100 --interval 300 --background
```

### Scenario 3: Custom Intervals

```bash
# Server: Change port every 120 seconds, periodic tasks every 5 minutes
sudo python3 sendtraffic.py --mode server --port 5201 --port-duration 120 --interval 300 --background

# Client: Periodic tasks every 5 minutes
sudo python3 sendtraffic.py --mode client --host 192.168.1.100 --interval 300 --background
```

### Scenario 4: Port Range with Cycling

```bash
# Server: Use ports 4000-5000, cycle back when max reached (each port for 30 seconds)
sudo python3 sendtraffic.py --mode server --port 4000 --max-port 5000 --port-duration 30 --background

# Client: Auto-sync to cycling ports
sudo python3 sendtraffic.py --mode client --host 192.168.1.100 --background
```

**Port sequence:** 4000 → 4001 → 4002 → ... → 5000 → 4000 → 4001 → ...


## Periodic Tasks (Every Interval)

The script automatically executes these tasks every interval (default: 600 seconds):

### 1. File Download
```
Downloads: http://testmynids.org/exe/calc.exe
Location: /tmp/calc.exe
Behavior: Deletes old file before downloading new one
```

### 2. Dummy Traffic
```
Type: iperf3 client (1 second burst)
Speed: 1 Mbps
Target: Port 6500 on specified host
```

### 3. Domain Blocking Verification
```
Domains checked:
- www.fb.com
- www.x.com
- www.instagram.com
- www.pinterest.com
- www.reddit.com
- www.snapchat.com

Timeout: 5 seconds per domain
Success: Any HTTP response (200, 403, 401, 500, etc.)
Failure: Connection errors or timeouts
```

**Example Output:**
```
[2026-06-11 12:10:00] Successfully downloaded http://testmynids.org/exe/calc.exe to /tmp/calc.exe
[2026-06-11 12:10:01] ✓ Sent dummy traffic to 192.168.1.100:6500
[2026-06-11 12:10:02] ✓ www.fb.com blocked successfully (HTTP 403)
[2026-06-11 12:10:03] ✓ www.x.com blocked successfully (HTTP 200)
[2026-06-11 12:10:04] ✓ www.instagram.com blocked successfully (HTTP 403)
[2026-06-11 12:10:05] ✓ www.pinterest.com blocked successfully (HTTP 403)
[2026-06-11 12:10:06] ✓ www.reddit.com blocked successfully (HTTP 200)
[2026-06-11 12:10:07] ✓ www.snapchat.com blocked successfully (HTTP 403)
```

## Port Rotation

Ports automatically increment at the specified interval and cycle back to the base port when max is reached:

### Without Port Range (Infinite Increment)
```
Port: 5201 → [30s] → 5202 → [30s] → 5203 → [30s] → 5204 → ...
```

**Usage:**
```bash
sudo python3 sendtraffic.py --mode server --port 5201 --background
```

### With Port Range (Cycles Back)
```
Port: 4000 → [30s] → 4001 → [30s] → 4002 → [30s] → 5000 → [cycles back] → 4000 → [30s] → 4001...
```

**Usage (port range 4000-5000):**
```bash
sudo python3 sendtraffic.py --mode server --port 4000 --max-port 5000 --background
```

**Output when cycling:**
```
▶ iperf3 server listening on port 5000 (discovery advertising this port)
⊘ Port 5000 timeout reached, moving to next port
Port range 4000-5000 completed, cycling back to 4000
▶ iperf3 server listening on port 4000 (discovery advertising this port)
```

**Change Port Duration:**
```bash
# Use each port for 60 seconds
sudo python3 sendtraffic.py --mode server --port 5201 --port-duration 60 --background

# Use each port for 10 seconds
sudo python3 sendtraffic.py --mode server --port 5201 --port-duration 10 --background

# Port range 4000-5000, each for 45 seconds
sudo python3 sendtraffic.py --mode server --port 4000 --max-port 5000 --port-duration 45 --background
```

## Port Synchronization

The server and client automatically sync via a discovery service:

1. **Server** opens port 9999 (discovery service)
2. **Server** reports current iperf3 port to clients
3. **Client** queries port 9999 to get current iperf3 port
4. **Client** automatically connects to the reported port
5. On port rotation, client auto-discovers new port

**No manual intervention needed!**

## Troubleshooting

### Client Can't Connect to Discovery Service

**Error:**
```
✗ Connection refused on 192.168.1.100:9999
✗ Discovery service timeout on 192.168.1.100:9999
```

**Solutions:**
1. Verify server is running: `ssh user@192.168.1.100 ps aux | grep sendtraffic`
2. Check firewall allows port 9999:
   ```bash
   sudo ufw allow 9999/tcp
   sudo ufw allow 5201:5210/tcp
   ```
3. Test connectivity:
   ```bash
   ping 192.168.1.100
   telnet 192.168.1.100 9999
   ```

### Dummy Traffic Fails

**Error:**
```
✗ Failed to send traffic to 192.168.1.100:6500
```

**Solution:** This is expected if there's no iperf3 server listening on port 6500. It's not critical.

### Domain Curl Fails

**Error:**
```
✗ www.fb.com blocking error: Connection refused
```

**Solutions:**
1. Check internet connectivity: `ping 8.8.8.8`
2. Verify DNS is working: `nslookup www.fb.com`
3. Check firewall allows outbound HTTPS: `sudo ufw allow out 443`

### Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:** Run with sudo:
```bash
sudo python3 sendtraffic.py --mode server --port 5201 --background
```

### iperf3 Not Found

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'iperf3'
```

**Solution:** Install iperf3:
```bash
sudo apt-get install iperf3     # Linux
brew install iperf3             # macOS
```

## Log Output Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Success/Blocked successfully |
| ✗ | Failure/Error |
| ▶ | Starting operation |
| ⊘ | Operation ended/rotated |
| ⚠ | Warning |

## Running as a Service (Optional)

### Create systemd Service (Linux)

```bash
sudo nano /etc/systemd/system/sendtraffic.service
```

**Content:**
```ini
[Unit]
Description=SendTraffic Network Traffic Generator
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sendtraffic
ExecStart=/usr/bin/python3 /opt/sendtraffic/sendtraffic.py --mode server --port 5201 --background
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and Start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable sendtraffic.service
sudo systemctl start sendtraffic.service
sudo systemctl status sendtraffic.service
```

## Notes

- Script runs indefinitely until interrupted with Ctrl+C
- All operations are logged with timestamps
- File downloads delete previous version before downloading new one
- HTTP 403/401/4xx responses are counted as "blocked successfully"
- Periodic tasks execute immediately on start, then repeat at specified interval
- Discovery service allows automatic port sync without manual configuration

## Support

For issues or feature requests, check the logs first:
- Look for ✗ errors
- Verify firewall rules
- Ensure all dependencies are installed
- Check network connectivity between machines
