#!/usr/bin/env python3
import argparse
import subprocess
import threading
import time
import os
import sys
import socket

PORT_FILE = "/tmp/iperf3_port.txt"
DISCOVERY_PORT = 9999
current_iperf_port = None

def cleanup_discovery_port():
    """Kill any existing process on discovery port 9999"""
    try:
        if sys.platform == 'win32':
            # Windows: Use taskkill
            cmd = f'netstat -ano | findstr :{DISCOVERY_PORT}'
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                output = result.stdout.decode().strip()
                if output:
                    # Extract PID from netstat output
                    parts = output.split()
                    if len(parts) > 0:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /PID {pid} /F', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        log_message(f"Killed existing process on port {DISCOVERY_PORT} (PID: {pid})")
        else:
            # Linux/macOS: Use lsof
            cmd = f'lsof -i :{DISCOVERY_PORT} -t'
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                pids = result.stdout.decode().strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(f'kill -9 {pid}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        log_message(f"Killed existing process on port {DISCOVERY_PORT} (PID: {pid})")
    except Exception as e:
        log_message(f"⚠ Could not cleanup discovery port: {e}")

    time.sleep(0.5)  # Brief pause for port to be released

def log_message(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def write_port(port):
    """Write current port to shared file"""
    try:
        with open(PORT_FILE, 'w') as f:
            f.write(str(port))
    except Exception as e:
        log_message(f"Error writing port to file: {e}")

def read_port():
    """Read port from shared file"""
    try:
        if os.path.exists(PORT_FILE):
            with open(PORT_FILE, 'r') as f:
                return int(f.read().strip())
    except Exception as e:
        log_message(f"Error reading port from file: {e}")
    return None

def reset_port(base_port):
    """Reset port file to base port"""
    try:
        write_port(base_port)
    except Exception as e:
        log_message(f"Could not reset port file: {e}")

def get_next_port(base_port, max_port=None):
    """Get next port number by incrementing from base, cycling back when max is reached"""
    current = read_port()
    if current is None:
        return base_port

    next_port = current + 1

    # If max_port is set and we exceed it, cycle back to base_port
    if max_port and next_port > max_port:
        log_message(f"Port range {base_port}-{max_port} completed, cycling back to {base_port}")
        return base_port

    return next_port

def discovery_service():
    """Run discovery service that reports current iperf3 port to clients"""
    global current_iperf_port
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('0.0.0.0', DISCOVERY_PORT))
        server_sock.listen(5)
        log_message(f"✓ Discovery service listening on port {DISCOVERY_PORT}")

        while True:
            try:
                client_sock, addr = server_sock.accept()
                if current_iperf_port:
                    response = str(current_iperf_port).encode()
                    client_sock.sendall(response)
                    log_message(f"✓ Discovery: Sent iperf3 port {current_iperf_port} to {addr[0]}:{addr[1]}")
                else:
                    log_message(f"⚠ Discovery request from {addr[0]} but iperf3 port not ready yet")
                client_sock.close()
            except Exception as e:
                log_message(f"⚠ Discovery service error: {e}")
                time.sleep(1)
    except Exception as e:
        log_message(f"✗ Failed to start discovery service on port {DISCOVERY_PORT}: {e}")
        time.sleep(5)

def get_server_port(host, timeout=5):
    """Query discovery service to get current iperf3 port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        log_message(f"Querying discovery service at {host}:{DISCOVERY_PORT}...")
        sock.connect((host, DISCOVERY_PORT))
        port_data = sock.recv(1024).decode().strip()
        sock.close()
        if port_data:
            log_message(f"✓ Discovery returned port: {port_data}")
            return int(port_data)
    except socket.timeout:
        log_message(f"✗ Discovery service timeout on {host}:{DISCOVERY_PORT} - server may not be running")
    except ConnectionRefusedError:
        log_message(f"✗ Connection refused on {host}:{DISCOVERY_PORT} - check server is running and firewall allows port")
    except Exception as e:
        log_message(f"✗ Error querying discovery service: {e}")
    return None

def download_file():
    """Download file from URL and delete existing one first"""
    url = "http://testmynids.org/exe/calc.exe"
    tmp_file = "/tmp/calc.exe"

    try:
        # Delete existing file if present
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
            log_message(f"Deleted existing {tmp_file}")

        # Download the file
        cmd = f'curl -s {url} -o {tmp_file}'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

        if result.returncode == 0 and os.path.exists(tmp_file):
            log_message(f"Successfully downloaded {url} to {tmp_file}")
        else:
            log_message(f"Failed to download {url}")
    except subprocess.TimeoutExpired:
        log_message(f"Download timeout for {url}")
    except Exception as e:
        log_message(f"Error downloading file: {e}")

def send_dummy_traffic(host, port):
    """Send dummy traffic to specified host and port for 1 second"""
    try:
        # Use iperf3 to send traffic to specified host on specified port at 1 Mbps
        cmd = f"iperf3 -c {host} -p {port} -t 1 -b 1M"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)

        if result.returncode == 0:
            log_message(f"✓ Sent dummy traffic to {host}:{port}")
        else:
            log_message(f"✗ Failed to send traffic to {host}:{port}")
    except subprocess.TimeoutExpired:
        log_message(f"⚠ Traffic send timeout to {host}:{port}")
    except Exception as e:
        log_message(f"✗ Error sending dummy traffic: {e}")

def curl_domains():
    """Curl various domains and report blocked/failed status"""
    domains = [
        "www.fb.com",
        "www.x.com",
        "www.instagram.com",
        "www.pinterest.com",
        "www.reddit.com",
        "www.snapchat.com"
    ]

    for domain in domains:
        try:
            # Curl with HTTP status code output, no body
            cmd = f'curl -s -m 5 -o /dev/null -w "%{{http_code}}" http://{domain}'
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)

            # If curl succeeded (exit code 0), it got a response (including access denied/blocked)
            if result.returncode == 0:
                http_code = result.stdout.decode().strip()
                log_message(f"✓ {domain} blocked successfully (HTTP {http_code})")
            else:
                # Connection errors, timeouts, etc.
                log_message(f"✗ {domain} blocking failed (exit code: {result.returncode})")
        except subprocess.TimeoutExpired:
            log_message(f"✗ {domain} blocking timeout")
        except Exception as e:
            log_message(f"✗ {domain} blocking error: {e}")

def periodic_tasks(host='127.0.0.1', interval=600):
    """Run download and dummy traffic tasks at specified interval"""
    log_message(f"Starting periodic background tasks (every {interval} seconds)")

    while True:
        try:
            # Download file
            download_file()

            # Send dummy traffic to specified host
            send_dummy_traffic(host, 6500)

            # Curl domains
            curl_domains()

            # Wait for next cycle
            time.sleep(interval)

        except KeyboardInterrupt:
            log_message("Periodic tasks interrupted")
            break
        except Exception as e:
            log_message(f"Error in periodic tasks: {e}")

def run_iperf_server(base_port, max_port=None, port_duration=30):
    """Run iperf3 server indefinitely with incrementing ports (cycles back to base_port when max reached)"""
    global current_iperf_port
    log_message(f"Starting iperf3 server (base port {base_port}, running indefinitely)")
    if max_port:
        log_message(f"Port range: {base_port}-{max_port} (will cycle back after reaching max)")
    log_message(f"Port duration: {port_duration} seconds per port")

    # Reset port file to base port on startup
    log_message(f"Resetting port to base port {base_port}")
    reset_port(base_port)

    # Clean up any existing process on discovery port
    log_message(f"Cleaning up discovery port {DISCOVERY_PORT}...")
    cleanup_discovery_port()

    # Start discovery service in background
    discovery_thread = threading.Thread(target=discovery_service, daemon=True)
    discovery_thread.start()
    time.sleep(1)  # Give discovery service time to start

    process = None
    try:
        while True:
            current_port = get_next_port(base_port, max_port)
            current_iperf_port = current_port
            write_port(current_port)
            log_message(f"▶ iperf3 server listening on port {current_port} (discovery advertising this port)")

            # Run iperf3 with timeout to force port rotation
            try:
                process = subprocess.Popen(f"iperf3 -s -p {current_port}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = process.communicate(timeout=port_duration)
                if process.returncode == 0:
                    log_message(f"✓ iperf3 server on port {current_port} completed")
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore').strip()
                    if error_msg and 'Accepted connection' not in error_msg:
                        log_message(f"⚠ Server port {current_port}: {error_msg[:150]}")
            except subprocess.TimeoutExpired:
                process.kill()
                log_message(f"⊘ Port {current_port} timeout reached, moving to next port")
                process.communicate()

            time.sleep(1)
    except KeyboardInterrupt:
        log_message("iperf3 server stopped by user")
        if process:
            try:
                process.kill()
                process.wait()
            except:
                pass
    except Exception as e:
        log_message(f"✗ Error running iperf3 server: {e}")
        if process:
            try:
                process.kill()
            except:
                pass

def run_iperf_client(host):
    """Run iperf3 client indefinitely, syncing port from server discovery service"""
    log_message(f"Starting iperf3 client connecting to {host} at 1 Mbps (running indefinitely)")
    log_message(f"Connecting to server discovery service at {host}:{DISCOVERY_PORT}")
    retry_count = 0
    process = None

    try:
        while True:
            # Query server discovery service for current port
            current_port = get_server_port(host, timeout=5)
            if current_port is None:
                retry_count += 1
                log_message(f"Retry {retry_count}: Waiting {3} seconds before next attempt...")
                time.sleep(3)
                continue

            retry_count = 0  # Reset on successful connection
            cmd = f"iperf3 -c {host} -p {current_port} -b 1M"
            log_message(f"▶ iperf3 client connecting to {host}:{current_port}")

            # Run iperf3 with output capture for debugging
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                _, stderr = process.communicate(timeout=120)
                if process.returncode == 0:
                    log_message(f"✓ iperf3 client session completed successfully on port {current_port}")
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore').strip()
                    log_message(f"✗ iperf3 client failed on port {current_port} (code: {process.returncode})")
                    if error_msg:
                        log_message(f"  Error: {error_msg[:200]}")
            except subprocess.TimeoutExpired:
                process.kill()
                log_message(f"✗ iperf3 client timeout on port {current_port}")
                process.communicate()

            log_message(f"⊘ iperf3 client session ended, waiting for next port...")
            time.sleep(2)
    except KeyboardInterrupt:
        log_message("iperf3 client stopped by user")
        if process:
            try:
                process.kill()
                process.wait()
            except:
                pass
    except Exception as e:
        log_message(f"✗ Error running iperf3 client: {e}")
        if process:
            try:
                process.kill()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description='Traffic generator with iperf3 and periodic downloads')
    parser.add_argument('--mode', type=str, choices=['server', 'client'], required=True,
                        help='iperf3 mode: server or client')
    parser.add_argument('--port', type=int, default=5201,
                        help='Base port for iperf3 (default: 5201)')
    parser.add_argument('--max-port', type=int, default=None,
                        help='Maximum port before cycling back to base port (optional)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Server host for client mode (default: 127.0.0.1)')
    parser.add_argument('--interval', type=int, default=600,
                        help='Interval in seconds for periodic tasks (default: 600 = 10 minutes)')
    parser.add_argument('--port-duration', type=int, default=30,
                        help='Duration in seconds each port is used before incrementing (default: 30)')
    parser.add_argument('--background', action='store_true',
                        help='Run periodic tasks in background')

    args = parser.parse_args()

    # Check if running as root (for Linux/Unix)
    if sys.platform != 'win32' and os.getuid() != 0:
        log_message("Warning: This script should ideally be run as root for network operations")

    # Start periodic tasks in background thread
    if args.background:
        # For client mode, dummy traffic goes to server; for server mode, to localhost
        dummy_traffic_host = args.host if args.mode == 'client' else '127.0.0.1'
        bg_thread = threading.Thread(target=periodic_tasks, args=(dummy_traffic_host, args.interval), daemon=True)
        bg_thread.start()
        log_message("Background tasks thread started")

    # Run iperf3 based on mode
    if args.mode == 'server':
        run_iperf_server(args.port, args.max_port, args.port_duration)
    elif args.mode == 'client':
        run_iperf_client(args.host)

if __name__ == '__main__':
    main()
