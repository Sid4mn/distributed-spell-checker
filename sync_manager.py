"""
Complete Sync Manager for Distributed Spell Checker
Keeps lexicons synchronized across servers
"""

import socket
import threading
import time
import json

class SyncManager:
    def __init__(self, node_id, lexicon_file, sync_port=8000):
        self.node_id = node_id
        self.lexicon_file = lexicon_file
        self.sync_port = sync_port
        self.peers = []  # List of peer servers
        self.lexicon_version = 0
        self.running = False
        self.sync_socket = None
        self.listener_thread = None
        
    def add_peer(self, peer_address):
        """Add a peer server to sync with"""
        if peer_address not in self.peers:
            self.peers.append(peer_address)
            print(f"[SYNC] Added peer: {peer_address}")
            
    def broadcast_update(self, new_words):
        """Send lexicon updates to all peers"""
        if not new_words:
            return
            
        self.lexicon_version += 1
        message = {
            'type': 'lexicon_update',
            'from': self.node_id,
            'version': self.lexicon_version,
            'words': list(new_words)
        }
        
        print(f"[SYNC] Broadcasting {len(new_words)} new words to {len(self.peers)} peers")
        
        for peer_host, peer_port in self.peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((peer_host, peer_port))
                sock.send(json.dumps(message).encode())
                sock.close()
                print(f"[SYNC] Successfully sent update to {peer_host}:{peer_port}")
            except Exception as e:
                print(f"[SYNC] Failed to send to {peer_host}:{peer_port}: {e}")
                
    def receive_update(self, message):
        """Process lexicon update from peer"""
        try:
            if message['version'] > self.lexicon_version:
                # Update our lexicon with new words
                new_words = message['words']
                
                # Read current lexicon
                with open(self.lexicon_file, 'r') as f:
                    current_words = f.read().strip().split()
                
                # Add new words that aren't already in lexicon
                words_added = []
                for word in new_words:
                    if word not in current_words:
                        current_words.append(word)
                        words_added.append(word)
                
                # Write updated lexicon
                if words_added:
                    with open(self.lexicon_file, 'w') as f:
                        f.write(' '.join(current_words))
                    
                    print(f"[SYNC] Received and added {len(words_added)} new words from {message['from']}")
                    print(f"[SYNC] New words: {', '.join(words_added[:5])}{'...' if len(words_added) > 5 else ''}")
                    self.lexicon_version = message['version']
                    return True
                    
        except Exception as e:
            print(f"[SYNC] Error processing update: {e}")
        return False
        
    def listen_for_updates(self):
        """Listen for incoming sync messages from peers"""
        try:
            self.sync_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sync_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sync_socket.bind(('localhost', self.sync_port))
            self.sync_socket.listen(5)
            
            print(f"[SYNC] Listening for sync updates on port {self.sync_port}")
            
            while self.running:
                try:
                    self.sync_socket.settimeout(1)  # Check for stop signal every second
                    conn, addr = self.sync_socket.accept()
                    
                    # Receive sync message
                    data = conn.recv(4096).decode()
                    if data:
                        message = json.loads(data)
                        self.receive_update(message)
                    
                    conn.close()
                    
                except socket.timeout:
                    continue  # Check if still running
                except Exception as e:
                    if self.running:
                        print(f"[SYNC] Error in listener: {e}")
                        
        except Exception as e:
            print(f"[SYNC] Failed to start listener: {e}")
        finally:
            if self.sync_socket:
                self.sync_socket.close()
                
    def start(self):
        """Start sync manager in background"""
        self.running = True
        self.listener_thread = threading.Thread(target=self.listen_for_updates, daemon=True)
        self.listener_thread.start()
        print(f"[SYNC] Sync manager started for {self.node_id}")
        
    def stop(self):
        """Stop sync manager"""
        self.running = False
        if self.sync_socket:
            try:
                self.sync_socket.close()
            except:
                pass
        print(f"[SYNC] Sync manager stopped for {self.node_id}")
        
    def get_status(self):
        """Get sync manager status"""
        return {
            'node_id': self.node_id,
            'version': self.lexicon_version,
            'peers': len(self.peers),
            'running': self.running
        }