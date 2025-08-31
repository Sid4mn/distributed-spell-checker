#!/usr/bin/env python3
"""
Test script to verify client-server connectivity
"""

import socket
import time

def test_direct_server(port):
    """Test direct connection to a server"""
    print(f"\nTesting direct connection to server on port {port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', port))
        print(f"  [OK] Connected to port {port}")
        
        # Send a test username
        sock.send(b"testuser")
        response = sock.recv(1024)
        print(f"  [OK] Server response: {response.decode()}")
        
        sock.close()
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

def test_load_balancer():
    """Test connection through load balancer"""
    print("\nTesting load balancer connection on port 7520...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 7520))
        print("  [OK] Connected to load balancer")
        
        # Send a test username
        sock.send(b"lbtest")
        response = sock.recv(1024)
        print(f"  [OK] Response via load balancer: {response.decode()}")
        
        sock.close()
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

def main():
    print("=" * 60)
    print("CONNECTIVITY TEST FOR DISTRIBUTED SPELL CHECKER")
    print("=" * 60)
    
    # Test servers directly
    server1_ok = test_direct_server(7530)
    server2_ok = test_direct_server(7531)
    
    # Test load balancer
    lb_ok = test_load_balancer()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print(f"  Server 1 (7530): {'PASS' if server1_ok else 'FAIL'}")
    print(f"  Server 2 (7531): {'PASS' if server2_ok else 'FAIL'}")
    print(f"  Load Balancer (7520): {'PASS' if lb_ok else 'FAIL'}")
    
    if all([server1_ok, server2_ok, lb_ok]):
        print("\n[SUCCESS] All components are working!")
        print("You can now connect clients to port 7520")
    else:
        print("\n[WARNING] Some components are not working")
        print("Check that all servers and load balancer are running")
    print("=" * 60)

if __name__ == "__main__":
    main()