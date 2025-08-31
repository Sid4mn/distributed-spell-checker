"""
Load Balancer for Spell Checker
Distributes clients between multiple servers
"""

import socket
import threading
import random
import json
import time
from health_monitor import HealthMonitor

class LoadBalancer:
    def __init__(self, port=7520):
        self.servers = []  
        self.port = port 
        self.active_connections = {} 
        self.health_monitor = HealthMonitor() 
        self.running = False 
        self.current_server_index = 0
        self.stats = { 
            'requests_handled': 0,
            'connections_forwarded': 0,
            'start_time': time.time()
        }
        
    def add_server(self, server_ip, server_port):
        """Add a new server to the load balancer"""
        server_addr = (server_ip, server_port)
        self.servers.append(server_addr)
        self.health_monitor.add_server(server_addr)
        print(f"[LOAD BALANCER] Added server {server_ip}:{server_port}")
        
    def get_best_server(self):
        """Pick the best server using round-robin distribution"""
        healthy_servers = self.health_monitor.get_healthy_servers()
        
        if not healthy_servers:
            print("[LOAD BALANCER] No healthy servers available!")
            return None
            
        print(f"[LOAD BALANCER] Healthy servers: {healthy_servers}")
        
        # Use round-robin instead of random selection
        if len(healthy_servers) == 1:
            selected_server = healthy_servers[0]
        else:
            # Round-robin selection
            selected_server = healthy_servers[self.current_server_index % len(healthy_servers)]
            self.current_server_index += 1
            
        print(f"[LOAD BALANCER] Selected server: {selected_server}")
        return selected_server
        
    def start(self):
        """Start the load balancer"""
        self.running = True
        self.health_monitor.start_monitoring() # start health checks
        
        # Create socket to listen for clients
        lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lb_socket.bind(('localhost', self.port))
        lb_socket.listen(5)
        
        print(f"[LOAD BALANCER] Listening on port {self.port}")
        
        while self.running:
            try:
                client_conn, client_addr = lb_socket.accept()
                self.stats['requests_handled'] += 1
                
                # Start thread to handle this client - FIX THIS PART
                threading.Thread(
                    target=self.handle_client,
                    args=(client_conn, client_addr)  # Pass client_addr not server_addr
                ).start()
                
            except Exception as e:
                print(f"[LOAD BALANCER ERROR] {e}")
                
        lb_socket.close()
        

    def handle_client(self, client_socket, client_addr):
        """Handle incoming client connection with fault tolerance"""
        max_retries = 2  # Try up to 2 different servers
        attempts = 0
        server_socket = None
        
        while attempts < max_retries:
            server = self.get_best_server()
            
            if not server:
                print(f"[ERROR] No healthy servers available")
                try:
                    client_socket.send(b"ERROR: No servers available")
                except:
                    pass
                break
                
            print(f"[ROUTING] Attempt {attempts + 1}: Client {client_addr} → Server {server}")
            
            try:
                # Try to connect to server
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.connect(server)
                
                # Connection successful, forward traffic
                print(f"[SUCCESS] Connected to {server}")
                self.forward_traffic(client_socket, server_socket)
                
                # If we get here, forwarding completed successfully
                self.stats['connections_forwarded'] += 1
                break
                
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                print(f"[FAILOVER] Server {server} failed: {e}")
                
                # Remove failed server from healthy list
                if server in self.health_monitor.healthy_servers:
                    self.health_monitor.healthy_servers.remove(server)
                    print(f"[HEALTH] Marked {server} as unhealthy")
                
                attempts += 1
                
                # Close the failed server socket
                if server_socket:
                    try:
                        server_socket.close()
                    except:
                        pass
                    server_socket = None
                    
                if attempts >= max_retries:
                    print(f"[ERROR] All servers failed")
                    try:
                        client_socket.send(b"ERROR: All servers unavailable")
                    except:
                        pass
        
        # Clean up sockets after forwarding is complete
        if server_socket:
            try:
                server_socket.close()
            except:
                pass
        try:
            client_socket.close()
        except:
            pass

    def forward_traffic(self, client_socket, server_socket):
        """Forward traffic between client and server bidirectionally"""
        try:
            # Set sockets to non-blocking would cause issues, keep them blocking
            
            # Create threads for bidirectional forwarding
            client_to_server = threading.Thread(
                target=self.forward_data,
                args=(client_socket, server_socket, "client->server"),
                daemon=True
            )
            server_to_client = threading.Thread(
                target=self.forward_data, 
                args=(server_socket, client_socket, "server->client"),
                daemon=True
            )
            
            # Start both forwarding threads
            client_to_server.start()
            server_to_client.start()
            
            # Wait for both to complete
            client_to_server.join()
            server_to_client.join()
            
        except Exception as e:
            print(f"[FORWARD ERROR] {e}")
            
    def forward_data(self, source, destination, direction):
        """Forward data from source socket to destination socket"""
        try:
            while True:
                # Set a timeout to prevent hanging
                source.settimeout(60)  # 60 second timeout for reads
                
                try:
                    data = source.recv(4096)  # Receive up to 4096 bytes
                    if not data:
                        print(f"[FORWARD] {direction} connection closed normally")
                        break
                        
                    destination.send(data)
                    
                except socket.timeout:
                    # Timeout is okay, just continue
                    continue
                    
        except Exception as e:
            if "Broken pipe" not in str(e):
                print(f"[FORWARD] {direction} ended: {e}")
        finally:
            pass
                
    def get_stats(self):
        """Get load balancer performance stats"""
        uptime = time.time() - self.stats['start_time']
        health_stats = self.health_monitor.get_server_stats()
        
        return {
            'uptime_seconds': uptime,
            'requests_handled': self.stats['requests_handled'],
            'connections_forwarded': self.stats['connections_forwarded'],
            'servers': health_stats
        }
        
    def stop(self):
        """Stop the load balancer"""
        self.running = False
        self.health_monitor.stop_monitoring()

    def debug_server_status(self):
        """Print current server status for debugging"""
        print(f"[DEBUG] Total registered servers: {len(self.servers)}")
        for server in self.servers:
            print(f"[DEBUG] Server: {server}")
            
        healthy = self.health_monitor.get_healthy_servers()
        print(f"[DEBUG] Healthy servers: {len(healthy)} - {healthy}")
        
        server_stats = self.health_monitor.get_server_stats()
        print(f"[DEBUG] Health monitor stats: {server_stats}")

if __name__ == "__main__":
    print("DISTRIBUTED SPELL CHECKER LOAD BALANCER")
    print("=" * 50)
    
    lb = LoadBalancer()
    
    # Add servers
    lb.add_server('localhost', 7530)
    lb.add_server('localhost', 7531)
    
    print("Load balancer starting on port 7520...")
    print("Registered servers:")
    for server in lb.servers:
        print(f"  - {server[0]}:{server[1]}")
    print("=" * 50)
    
    # Start health monitoring first
    lb.health_monitor.start_monitoring()
    
    # Give health monitor time to check servers
    print("Waiting for initial health checks...")
    time.sleep(3)
    
    try:
        lb.start()
    except KeyboardInterrupt:
        print("\n[LOAD BALANCER] Shutting down...")
        lb.stop()