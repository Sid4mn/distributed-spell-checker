"""
Health Monitor for Spell Checker Servers
Checks if servers are working properly
"""

import socket
import threading
import time
import json

class HealthMonitor:
    def __init__(self, check_interval=10):
        self.servers = {} 
        self.healthy_servers = [] 
        self.check_interval = check_interval
        self.monitoring = False
        
    def add_server(self, server_addr):
        """Add a new server to monitor"""
        self.servers[server_addr] = {
            'status': 'unknown',
            'last_check': 0,
            'response_time': 0,
            'failed_checks': 0
        }
        
    def ping_server(self, server_addr):
        """Send a ping to check if server is alive"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(server_addr)
            sock.send(b"HEARTBEAT")
            response = sock.recv(1024)
            sock.close()
            
            response_time = time.time() - start_time
            
            if response == b"ALIVE":
                self.servers[server_addr]['status'] = 'healthy'
                self.servers[server_addr]['response_time'] = response_time
                self.servers[server_addr]['failed_checks'] = 0
                
                if server_addr not in self.healthy_servers:
                    self.healthy_servers.append(server_addr)
                    print(f"[HEALTH] Server {server_addr} is now HEALTHY")
                return True
                
        except Exception as e:
            # Server didn't respond or connection failed
            self.servers[server_addr]['failed_checks'] += 1
            if self.servers[server_addr]['failed_checks'] >= 3:
                self.servers[server_addr]['status'] = 'unhealthy'
                
                if server_addr in self.healthy_servers:
                    self.healthy_servers.remove(server_addr)
                    print(f"[HEALTH] Server {server_addr} is now UNHEALTHY")
            return False
            
    def get_healthy_servers(self):
        """Get list of servers that are working"""
        return self.healthy_servers.copy()  # Return copy of healthy servers list
        
    def start_monitoring(self):
        """Start checking servers continuously"""
        self.monitoring = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        
    def stop_monitoring(self):
        """Stop monitoring servers"""
        self.monitoring = False
        
    def _monitor_loop(self):
        """Main loop that checks all servers"""
        while self.monitoring:
            for server_addr in self.servers:
                self.ping_server(server_addr)
                self.servers[server_addr]['last_check'] = time.time()
            time.sleep(self.check_interval)
            
    def get_server_stats(self):
        """Get summary of all monitored servers"""
        return {
            'total_servers': len(self.servers),
            'healthy_servers': len(self.get_healthy_servers()),
            'servers': self.servers
        }
