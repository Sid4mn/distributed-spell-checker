"""
SIDDHANT SHETTIWAR
Multi-Client Spell Checker Server
A distributed spell checking system using socket programming
"""

import socket
import threading
import tkinter as tk
import time
import json
import hashlib
import sys
from cache_manager import SpellCheckCache
from health_monitor import HealthMonitor
from sync_manager import SyncManager

#=================================================================================================================
"""Declaring global variables"""
#=================================================================================================================
IP = socket.gethostbyname(socket.gethostname()) # get our IP address automatically

# Check command line arguments for port
if len(sys.argv) > 1:
    # Support both "python server.py 7530" and "python server.py --port 7530"
    if sys.argv[1] == '--port' and len(sys.argv) > 2:
        PORT = int(sys.argv[2])
    else:
        PORT = int(sys.argv[1])
else:
    PORT = 7530 # default port

SYNC_PORT = PORT + 1000 # sync port is always PORT + 1000 (8530, 8531, etc)
SIZE = 1024
FORMAT = "utf-8"
clients = {} 
clients_lock = threading.Lock() 
PATH = "server/"
usernames = set()
usernames_lock = threading.Lock() 

ADDR = (IP, PORT)
SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SERVER.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
SERVER.bind(ADDR)

NODE_ID = f"server_{PORT}"

# Initialize cache with 500 entries max, 1 hour TTL
cache = SpellCheckCache(max_size=500, ttl=3600)

# Server statistics
server_stats = {
    'requests_processed': 0,
    'cache_hits': 0,
    'total_clients_served': 0,
    'uptime_start': time.time()
}

#=================================================================================================================

"""Reading lexicon data and splitting it with respect to space for comparison, saving it into a global list: lex_words_list[]."""
lex_file = "server/lexicon.txt"
with open(lex_file, "r") as f:
    lex_data = f.read()
lex_words_list = lex_data.strip().split(" ")  

# Initialize sync manager for inter-server communication
sync_manager = SyncManager(
    node_id=NODE_ID,
    lexicon_file=lex_file,
    sync_port=SYNC_PORT
)

if PORT == 7530:
    sync_manager.add_peer(('localhost', 8531))  # Connect to Server 2's sync port
elif PORT == 7531:
    sync_manager.add_peer(('localhost', 8530))  # Connect to Server 1's sync port

sync_manager.start()

def lexicon_check(data):
    """This function takes the data from the client and compares it with the lexicon
    present in the lexicon.txt and returns the updated data"""
    global lex_words_list
    
    # Simple lexicon check without cache (cache is handled in handle_client)
    words = data.strip().split(" ")
    updated_data = []
    for word in words:
        # Check if word (without punctuation) is in lexicon
        clean_word = word.strip('.,!?;:').lower()
        if clean_word in lex_words_list:
            updated_data.append(f"[{word}]")
        else:
            updated_data.append(word)

    return " ".join(updated_data)

def display_stats():
    """Display server and cache statistics in GUI - runs periodically"""
    try:
        stats = cache.get_stats()
        uptime = time.time() - server_stats['uptime_start']
        
        stats_text = f"[STATS UPDATE] Cache: {stats['hit_rate']} hit rate, {stats['size']}/{stats['max_size']} entries, Uptime: {uptime:.0f}s, Active Clients: {len(clients)}\n"
        msg.insert(tk.END, stats_text)
        msg.insert(tk.END, "-" * 60 + "\n")
        auto_scroll(msg)
    except Exception as e:
        msg.insert(tk.END, f"[STATS ERROR]: {e}\n")
        auto_scroll(msg)

def auto_scroll(listbox):
    """Auto-scroll to bottom"""
    listbox.yview_moveto(1.0)  # Always scroll to bottom
    listbox.update_idletasks()  # Force GUI update

def remove_client(conn, username):
    """Safely remove a client from all tracking structures"""
    with clients_lock:
        if conn in clients:
            del clients[conn]
    
    with usernames_lock:
        if username in usernames:
            usernames.discard(username)
    
    # Update GUI listbox
    try:
        for i, listbox_entry in enumerate(active_users.get(0, tk.END)):
            if username in listbox_entry:
                active_users.delete(i)
                break
    except:
        pass
    
    msg.insert(tk.END, f"[CLEANUP]: Removed {username} from all tracking structures\n")
    auto_scroll(msg)

"""This function handles the multiple clients and the process of lexicon spell check"""
def handle_client(conn, addr):
    global lex_words_list, server_stats
    username = None
    
    try:
        # Receive username or heartbeat
        conn.settimeout(5)
        cname = conn.recv(SIZE).decode(FORMAT)
        conn.settimeout(None)
        
        # Check if it's a heartbeat
        if cname == "HEARTBEAT":
            conn.send(b"ALIVE")
            heartbeat_msg.insert(tk.END, f"[HEARTBEAT] Health check from monitor @ {addr[0]}:{addr[1]}\n")
            auto_scroll(heartbeat_msg)
            conn.close()
            return
        
        username = cname
        
        # Check for username collision
        with usernames_lock:
            if username in usernames:
                conn.send("exists".encode(FORMAT))
                msg.insert(tk.END, f"[COLLISION]: Username '{username}' already exists, rejecting connection\n")
                auto_scroll(msg)
                conn.close()
                return
            else:
                usernames.add(username)
        
        # Add to clients dictionary
        with clients_lock:
            clients[conn] = username
        
        # Update GUI
        msg.insert(tk.END, f"[CONNECTED]: {username} has connected from {addr}\n")
        msg.insert(tk.END, f"[SERVER INFO]: Server {NODE_ID} is now handling {username}'s connection\n")
        auto_scroll(msg)
        active_users.insert(tk.END, f"{username} @ {addr[0]}:{addr[1]}")
        auto_scroll(active_users)
        server_stats['total_clients_served'] += 1
        
        # Send acceptance
        conn.send("accept".encode(FORMAT))
        
        # Main client communication loop
        while True:
            try:
                # Set socket timeout for recv
                conn.settimeout(60.0)  # 60 second timeout
                data = conn.recv(SIZE)
                
                if not data:
                    # Empty data means connection closed
                    msg.insert(tk.END, f"[DISCONNECT]: {username} connection closed (empty data)\n")
                    auto_scroll(msg)
                    break
                
                data = data.decode(FORMAT)
                
                if data == "Disconnect_Client":
                    msg.insert(tk.END, f"[DISCONNECT]: {username} requested disconnect\n")
                    auto_scroll(msg)
                    break
                    
                elif data == "LEXICON_POLL" or data == "PollingRequest":
                    # Server is polling client for lexicon updates
                    msg.insert(tk.END, f"[POLLING]: Requesting lexicon updates from {username}\n")
                    auto_scroll(msg)
                    # Client will respond with their words or "NO"
                    
                elif data.startswith("lexicon_response:"):
                    # Client sending lexicon words back to server
                    words_data = data[17:]  # Remove "lexicon_response:" prefix
                    
                    if words_data and words_data != "NO":
                        new_words = words_data.split(',')
                        added_count = 0
                        added_words = []
                        
                        # Add to global lexicon list
                        for word in new_words:
                            word = word.strip().lower()
                            if word and word not in lex_words_list:
                                lex_words_list.append(word)
                                added_words.append(word)
                                added_count += 1
                        
                        if added_count > 0:
                            # Update lexicon file
                            with open(lex_file, 'w') as f:
                                f.write(' '.join(lex_words_list))
                            
                            # Clear cache since lexicon changed
                            cache.clear()
                            
                            msg.insert(tk.END, f"[LEXICON UPDATE]: Added {added_count} new words from {username}\n")
                            msg.insert(tk.END, f"[NEW WORDS]: {', '.join(added_words[:5])}{'...' if len(added_words) > 5 else ''}\n")
                            msg.insert(tk.END, f"[CACHE]: Cache cleared due to lexicon update\n")
                            
                            # BROADCAST TO OTHER SERVERS - THIS IS THE KEY PART
                            sync_manager.broadcast_update(added_words)
                            msg.insert(tk.END, f"[SYNC]: Broadcasting {added_count} words to peer servers\n")
                            
                            auto_scroll(msg)
                            
                            # Send confirmation to client
                            conn.send("PollingSuccess".encode(FORMAT))
                        else:
                            conn.send("NoNewWords".encode(FORMAT))
                    else:
                        msg.insert(tk.END, f"[POLL]: {username} has no lexicon updates\n")
                        auto_scroll(msg)
                    
                elif data[:1] == "Y":
                    # Handle file spell check
                    filename = data[1:]
                    msg.insert(tk.END, f"[FILE]: {filename} uploaded by {username}\n")
                    auto_scroll(msg)
                    
                    # Receive file content
                    file_content = conn.recv(SIZE).decode(FORMAT)
                    
                    msg.insert(tk.END, f"[RECEIVED]: File content ({len(file_content)} chars)\n")
                    auto_scroll(msg)
                    
                    # Check cache first (cache key is the file content)
                    cached_result = cache.get(file_content)
                    
                    if cached_result:
                        # CACHE HIT
                        server_stats['cache_hits'] += 1
                        msg.insert(tk.END, f"[CACHE HIT]: Using cached result\n")
                        stats = cache.get_stats()
                        msg.insert(tk.END, f"[CACHE INFO]: {stats['hit_rate']} hit rate, {stats['size']}/{stats['max_size']} entries\n")
                        auto_scroll(msg)
                        updated_data = cached_result
                    else:
                        # CACHE MISS - Process the file
                        msg.insert(tk.END, f"[CACHE MISS]: Processing new text\n")
                        auto_scroll(msg)
                        
                        # Process with lexicon_check (but without cache - we'll cache here)
                        # Temporarily remove cache from lexicon_check
                        words = file_content.strip().split(" ")
                        updated_data = []
                        for word in words:
                            # Remove punctuation for checking but keep it in output
                            clean_word = word.strip('.,!?;:').lower()
                            if clean_word in lex_words_list:
                                updated_data.append(f"[{word}]")
                            else:
                                updated_data.append(word)
                        updated_data = " ".join(updated_data)
                        
                        # Now cache the result
                        cache.put(file_content, updated_data)
                        server_stats['requests_processed'] += 1
                        
                        stats = cache.get_stats()
                        msg.insert(tk.END, f"[CACHED]: Result stored in cache\n")
                        msg.insert(tk.END, f"[CACHE INFO]: {stats['hit_rate']} hit rate, {stats['size']}/{stats['max_size']} entries\n")
                        auto_scroll(msg)
                    
                    # Send back to client
                    response = "check" + updated_data
                    conn.send(response.encode(FORMAT))
                    msg.insert(tk.END, f"[SENT]: Corrected text sent to {username}\n")
                    msg.insert(tk.END, "-" * 60 + "\n")
                    auto_scroll(msg)
                    
            except socket.timeout:
                # Timeout is normal, just continue
                continue
                
            except ConnectionResetError:
                msg.insert(tk.END, f"[ERROR]: Connection reset by {username}\n")
                auto_scroll(msg)
                break
                
            except Exception as e:
                msg.insert(tk.END, f"[ERROR]: Error handling {username}: {e}\n")
                auto_scroll(msg)
                break
    
    except Exception as e:
        if "HEARTBEAT" not in str(e):
            msg.insert(tk.END, f"[ERROR]: Fatal error with client: {e}\n")
            auto_scroll(msg)
    
    finally:
        # Clean up the client
        if username:
            remove_client(conn, username)
            msg.insert(tk.END, f"[DISCONNECTED]: {username} has disconnected from Server {NODE_ID}\n")
            auto_scroll(msg)
        
        try:
            conn.close()
        except:
            pass

def connect():
    """Main server listening function"""
    SERVER.listen(5)
    msg.insert(tk.END, f"[LISTENING] Server {NODE_ID} listening on {IP}:{PORT}\n")
    auto_scroll(msg)
    
    while True:
        try:
            conn, addr = SERVER.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True  # Make threads daemon so they close with main program
            thread.start()
        except Exception as e:
            msg.insert(tk.END, f"[ERROR]: Error accepting connection: {e}\n")
            auto_scroll(msg)
            continue

def periodic_updates():
    """Periodically update statistics and poll clients for lexicon"""
    while True:
        time.sleep(5) 
        try:
            display_stats()
            
            # Poll all connected clients for lexicon updates
            with clients_lock:
                for conn, username in list(clients.items()):
                    try:
                        conn.send("LEXICON_POLL".encode(FORMAT))
                        msg.insert(tk.END, f"[POLLING]: Checking {username} for lexicon updates\n")
                        auto_scroll(msg)
                    except:
                        # Client disconnected, will be cleaned up later
                        pass
        except:
            pass

def handle_sync_updates():
    """Check for sync updates from other servers and update our lexicon"""
    global lex_words_list
    
    while True:
        time.sleep(2)  # Check every 2 seconds
        try:
            # Check if sync manager received any updates
            # This is a passive check - the sync manager's listener handles the actual receiving
            # We just need to reload the lexicon if it was updated
            with open(lex_file, 'r') as f:
                current_lexicon = f.read().strip().split()
            
            # If lexicon changed, update our in-memory list
            if len(current_lexicon) != len(lex_words_list):
                lex_words_list = current_lexicon
                msg.insert(tk.END, f"[SYNC RECEIVED]: Lexicon updated from peer server\n")
                msg.insert(tk.END, f"[LEXICON]: Now tracking {len(lex_words_list)} words\n")
                cache.clear()  # Clear cache since lexicon changed
                auto_scroll(msg)
        except:
            pass

# Then start this thread after the periodic_updates thread (around line 430):
sync_thread = threading.Thread(target=handle_sync_updates, daemon=True)
sync_thread.start()

# GUI Setup
window = tk.Tk()
window.title(f"SERVER NODE: {NODE_ID} | Port: {PORT} | Sync Port: {SYNC_PORT}")
window.configure(bg='#E8F4FD')
window.geometry("1200x600")  # Set larger default size
# Create main frame
main_frame = tk.Frame(window, bg='#E8F4FD')
main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Left side - Split into Active users and Heartbeat monitor
left_frame = tk.Frame(main_frame, bg='#E8F4FD', width=350)
left_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.BOTH, expand=False)
left_frame.pack_propagate(False)  # Maintain fixed width

# Top left - Active users
users_frame = tk.Frame(left_frame, bg='#E8F4FD')
users_frame.pack(fill=tk.BOTH, expand=True)

users_label = tk.Label(users_frame, text="ACTIVE CONNECTIONS", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
users_label.pack()

users_listbox_frame = tk.Frame(users_frame)
users_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5)

users_scrollbar = tk.Scrollbar(users_listbox_frame)
users_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

active_users = tk.Listbox(users_listbox_frame, height=10, width=40, bg='white', fg='#2C3E50', font=('Arial', 9), yscrollcommand=users_scrollbar.set)
active_users.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
users_scrollbar.config(command=active_users.yview)

# Bottom left - Heartbeat monitor
heartbeat_frame = tk.Frame(left_frame, bg='#E8F4FD')
heartbeat_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

heartbeat_label = tk.Label(heartbeat_frame, text="HEALTH MONITOR", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
heartbeat_label.pack()

heartbeat_listbox_frame = tk.Frame(heartbeat_frame)
heartbeat_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5)

heartbeat_scrollbar = tk.Scrollbar(heartbeat_listbox_frame)
heartbeat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

heartbeat_msg = tk.Listbox(heartbeat_listbox_frame, height=8, width=40, bg='#F5F5F5', fg='#666666', font=('Arial', 8), yscrollcommand=heartbeat_scrollbar.set)
heartbeat_msg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
heartbeat_scrollbar.config(command=heartbeat_msg.yview)

# Right side - Activity log
right_frame = tk.Frame(main_frame, bg='#E8F4FD')
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

activity_label = tk.Label(right_frame, text="SERVER ACTIVITY LOG", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
activity_label.pack()

msg_frame = tk.Frame(right_frame)
msg_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

scrollbar = tk.Scrollbar(msg_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

msg = tk.Listbox(msg_frame, height=20, width=100, yscrollcommand=scrollbar.set, bg='white', fg='#2C3E50', font=('Arial', 9))
msg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=msg.yview)

# Status bar
status_frame = tk.Frame(window, bg='#2980B9', height=25)
status_frame.pack(fill=tk.X, side=tk.BOTTOM)

status_label = tk.Label(status_frame, text=f"Server running on {IP}:{PORT} | Sync Port: {SYNC_PORT}", fg='white', bg='#2980B9', font=('Arial', 9))
status_label.pack(pady=3)

# Initial messages (no emojis)
msg.insert(tk.END, "=" * 80)
msg.insert(tk.END, f"SERVER NODE: {NODE_ID}")
msg.insert(tk.END, f"IP Address: {IP}")
msg.insert(tk.END, f"Main Port: {PORT}")
msg.insert(tk.END, f"Sync Port: {SYNC_PORT}")
msg.insert(tk.END, f"Cache Size: {cache.max_size} entries")
msg.insert(tk.END, f"Lexicon loaded: {len(lex_words_list)} words")
msg.insert(tk.END, "=" * 80)

# Start server listening thread
connect_thread = threading.Thread(target=connect)
connect_thread.daemon = True
connect_thread.start()

# Start periodic updates thread (no client polling)
update_thread = threading.Thread(target=periodic_updates)
update_thread.daemon = True
update_thread.start()

# Run GUI
tk.mainloop()

# Save lexicon when server closes
with open(lex_file, 'w+') as f:
    write_to_file = ' '.join(lex_words_list)
    f.write(write_to_file)

SERVER.close()