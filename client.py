"""
Multi-Client Spell Checker Client
A distributed spell checking system using socket programming
"""

import socket 
import threading 
import tkinter as tk 
from tkinter import messagebox 
import json
import time

#=================================================================================================================
"""Declaring global variables"""
#=================================================================================================================
SIZE = 1024
FORMAT = "utf-8"
CLIENT = None
PATH_send = "client/send/"
PATH_recv = "client/recv/"
SEND_DIR = "client/send/"
RECV_DIR = "client/recv/"
wordsList = []
dconflag = tk.StringVar
username = None
connected = False

#=================================================================================================================

def auto_scroll(listbox):
    """Auto-scroll to bottom"""
    listbox.yview_moveto(1.0)  # Always scroll to bottom
    listbox.update_idletasks()  # Force GUI update

def connect():
    """Connect to the server (or load balancer)"""
    global CLIENT, username, connected
    
    # Get connection details from entry fields
    username = username_entry.get().strip()
    server = server_entry.get().strip()
    port = port_entry.get().strip()
    
    # Validate username
    if not username:
        msg.insert(tk.END, "[ERROR]: Cannot connect with empty username. Please enter a valid username.\n")
        auto_scroll(msg)
        messagebox.showerror("Connection Error", "Please enter a username")
        return
    
    # Validate server
    if not server:
        server = "localhost"  # Default to localhost
        server_entry.insert(0, "localhost")
    
    # Validate port
    try:
        port = int(port) if port else 7520  # Default to load balancer port
        port_entry.delete(0, tk.END)
        port_entry.insert(0, str(port))
    except ValueError:
        msg.insert(tk.END, "[ERROR]: Invalid port number. Using default port 7520.\n")
        auto_scroll(msg)
        port = 7520
        port_entry.delete(0, tk.END)
        port_entry.insert(0, "7520")
    
    try:
        # Create socket and connect
        CLIENT = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CLIENT.settimeout(10)  # 10 second timeout for connection
        
        msg.insert(tk.END, f"[CONNECTING]: Attempting to connect to {server}:{port} as '{username}'...\n")
        auto_scroll(msg)
        CLIENT.connect((server, port))
        CLIENT.settimeout(None)  # Remove timeout after successful connection
        
        # Send username
        CLIENT.send(username.encode(FORMAT))
        
        # Wait for server response
        response = CLIENT.recv(SIZE).decode(FORMAT)
        
        if response == "exists":
            msg.insert(tk.END, f"[ERROR]: Username '{username}' already exists. Please try a different name.\n")
            auto_scroll(msg)
            messagebox.showerror("Username Error", f"Username '{username}' is already taken!")
            CLIENT.close()
            CLIENT = None
            return
        
        elif response == "accept":
            connected = True
            msg.insert(tk.END, f"[CONNECTED]: Successfully connected to server as '{username}'\n")
            msg.insert(tk.END, f"[INFO]: Connected via {server}:{port}\n")
            msg.insert(tk.END, "-" * 60 + "\n")
            auto_scroll(msg)
            
            # Update GUI
            status_label.configure(text=f"Status: Connected as {username}", fg="#27AE60")
            connect_button.configure(text="Connected", bg="#27AE60", fg='black', state=tk.DISABLED)
            disconnect_button.configure(state=tk.NORMAL)
            submit_button.configure(state=tk.NORMAL)
            add_word_button.configure(state=tk.NORMAL)
            
            # Start receive thread
            receive_thread = threading.Thread(target=receive)
            receive_thread.daemon = True
            receive_thread.start()
            
    except socket.timeout:
        msg.insert(tk.END, f"[ERROR]: Connection timeout. Server at {server}:{port} not responding.\n")
        auto_scroll(msg)
        messagebox.showerror("Connection Error", f"Cannot connect to {server}:{port}")
        CLIENT = None
    except Exception as e:
        msg.insert(tk.END, f"[ERROR]: Failed to connect - {e}\n")
        auto_scroll(msg)
        messagebox.showerror("Connection Error", f"Failed to connect: {e}")
        CLIENT = None

def disconnect():
    """Disconnect from the server"""
    global CLIENT, connected, username
    
    if CLIENT and connected:
        msg.insert(tk.END, "[DISCONNECTING]: Disconnecting from server...\n")
        auto_scroll(msg)
        try:
            CLIENT.send("Disconnect_Client".encode(FORMAT))
            time.sleep(0.1)  # Give server time to process
        except:
            pass
        
        CLIENT.close()
        CLIENT = None
        connected = False
        
        # Update GUI
        msg.insert(tk.END, "[DISCONNECTED]: You are now disconnected from the server.\n")
        msg.insert(tk.END, "-" * 60 + "\n")
        auto_scroll(msg)

        status_label.configure(text="Status: Not Connected", fg="#E74C3C")
        connect_button.configure(text="Connect", bg="#3498DB", fg='black', state=tk.NORMAL)
        disconnect_button.configure(state=tk.DISABLED)
        submit_button.configure(state=tk.DISABLED)
        add_word_button.configure(state=tk.DISABLED)

def receive():
    """Continuously receive messages from server"""

    global CLIENT, connected, wordsList
    
    while connected and CLIENT:
        try:
            data = CLIENT.recv(SIZE).decode(FORMAT)
            if not data:
                break
                
            # Handle different message types
            if data.startswith("check"):
                # Server sent corrected text
                corrected_content = data[5:]  # Remove "check" prefix
                
                # Get the filename that was submitted
                last_filename = getattr(receive, 'last_filename', 'unknown.txt')
                base_name = last_filename.replace('.txt', '')
                corrected_filename = f"corrected_{base_name}.txt"
                
                # Save corrected file
                with open(f"{RECV_DIR}{corrected_filename}", "w") as f:
                    f.write(corrected_content)
                    
                msg.insert(tk.END, f"[SAVED]: Corrected file saved as '{corrected_filename}'\n")
                msg.insert(tk.END, f"[RESULT]: Words in brackets [] are in the faulty lexicon\n")
                msg.insert(tk.END, f"[PREVIEW]: {corrected_content[:100]}...\n" if len(corrected_content) > 100 else f"[PREVIEW]: {corrected_content}\n")
                msg.insert(tk.END, "-" * 60 + "\n")

                auto_scroll(msg)
                
            elif data == "PollingSuccess":
                msg.insert(tk.END, "[LEXICON]: Server confirmed lexicon update\n")
                wordsList.clear()
                lexicon_listbox.delete(0, tk.END)
                auto_scroll(msg)

            elif data == "LEXICON_POLL" or data == "POLL":
                # Server is polling for lexicon updates
                msg.insert(tk.END, "[POLL]: Server requesting lexicon updates...\n")
                auto_scroll(msg)
                
                if wordsList:
                    # Send our words to server with proper prefix
                    words_to_send = ','.join(wordsList)
                    CLIENT.send(f"lexicon_response:{words_to_send}".encode(FORMAT))
                    msg.insert(tk.END, f"[SENT]: Sent {len(wordsList)} words to server\n")
                    msg.insert(tk.END, f"[WORDS]: {', '.join(wordsList[:5])}{'...' if len(wordsList) > 5 else ''}\n")
                    auto_scroll(msg)
                else:
                    CLIENT.send("lexicon_response:NO".encode(FORMAT))
                    msg.insert(tk.END, "[POLL]: No words to send\n")
                    auto_scroll(msg)
                    
            elif data == "PollingSuccess":
                msg.insert(tk.END, "[SUCCESS]: Server updated lexicon with your words!\n")
                msg.insert(tk.END, "[INFO]: These words will now be flagged in all future checks\n")
                auto_scroll(msg)
                
                # Clear the lexicon list and GUI
                wordsList.clear()
                lexicon_listbox.delete(0, tk.END)
                msg.insert(tk.END, "[CLEARED]: Lexicon management list cleared\n")
                msg.insert(tk.END, "-" * 60 + "\n")
                auto_scroll(msg)
                
            else:
                # Regular server message
                msg.insert(tk.END, f"[SERVER]: {data}\n")
                auto_scroll(msg)
                
        except Exception as e:
            if connected:
                msg.insert(tk.END, f"[ERROR]: Connection lost - {e}\n")
                auto_scroll(msg)
            break

def submit_file():
    """Submit a file for spell checking"""
    global CLIENT
    
    if not CLIENT or not connected:
        msg.insert(tk.END, "[ERROR]: Not connected to server.\n")
        auto_scroll(msg)
        return

    file_name = filename_entry.get().strip()
    
    # Store filename for receive function
    receive.last_filename = file_name

    # Validate filename
    if not file_name:
        msg.insert(tk.END, "[ERROR]: Cannot submit empty filename. Please enter a valid filename.\n")
        auto_scroll(msg)
        messagebox.showwarning("Input Error", "Please enter a filename")
        return
    
    # Check if it's a txt file
    if not file_name.endswith('.txt'):
        msg.insert(tk.END, f"[WARNING]: '{file_name}' should be a .txt file for best results.\n")
        auto_scroll(msg)
    
    # Try to read and send file
    try:
        with open(f"{SEND_DIR}{file_name}", "r") as f:
            file_content = f.read()
        
        msg.insert(tk.END, f"[SENDING]: Submitting '{file_name}' for spell check...\n")
        msg.insert(tk.END, f"[FILE CONTENT]: {file_content[:100]}...\n" if len(file_content) > 100 else f"[FILE CONTENT]: {file_content}\n")
        auto_scroll(msg)
        
        # Send file indicator and name
        CLIENT.send(f"Y{file_name}".encode(FORMAT))
        time.sleep(0.1)  # Small delay
        
        # Send file content
        CLIENT.send(file_content.encode(FORMAT))
        
        msg.insert(tk.END, f"[SENT]: File '{file_name}' sent to server for processing.\n")
        auto_scroll(msg)
        
        # Clear filename entry after successful submission
        filename_entry.delete(0, tk.END)
        
    except FileNotFoundError:
        msg.insert(tk.END, f"[ERROR]: File '{file_name}' not found in {SEND_DIR}\n")
        auto_scroll(msg)
        messagebox.showerror("File Error", f"File '{file_name}' not found in send folder")
    except Exception as e:
        msg.insert(tk.END, f"[ERROR]: Failed to send file - {e}\n")
        auto_scroll(msg)

def add_words():
    """Add words to lexicon list"""
    global wordsList
    word = lexicon_entry.get().strip()
    
    # Validate word
    if not word:
        msg.insert(tk.END, "[ERROR]: Cannot add empty words to lexicon. Please enter a valid word.\n")
        auto_scroll(msg)
        return
    
    # Check for duplicates
    if word in wordsList:
        msg.insert(tk.END, f"[WARNING]: '{word}' already added to lexicon list.\n")
        auto_scroll(msg)
        return
    
    # Add word
    wordsList.append(word)
    lexicon_listbox.insert(tk.END, word)
    msg.insert(tk.END, f"[LEXICON]: Added '{word}' to lexicon update list.\n")
    auto_scroll(msg)
    
    # Clear entry
    lexicon_entry.delete(0, tk.END)

# GUI Setup
window = tk.Tk()
window.title("SPELL CHECKER CLIENT")
window.configure(bg='#E8F4FD')
window.geometry("1000x650")  # Set larger default size

# Main container
main_container = tk.Frame(window, bg='#E8F4FD')
main_container.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Top section - Connection
connection_frame = tk.Frame(main_container, bg='#E8F4FD', relief=tk.RAISED, bd=2)
connection_frame.pack(fill=tk.X, pady=(0, 10))

inner_conn_frame = tk.Frame(connection_frame, bg='#E8F4FD')
inner_conn_frame.pack(expand=True)

conn_label = tk.Label(inner_conn_frame, text="CONNECTION SETTINGS", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
conn_label.grid(row=0, column=0, columnspan=6, pady=5)

# Connection inputs
tk.Label(inner_conn_frame, text="Username:", bg='#E8F4FD', fg='#2C3E50').grid(row=1, column=0, padx=5, pady=5, sticky='e')
username_entry = tk.Entry(inner_conn_frame, width=15)
username_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(inner_conn_frame, text="Server:", bg='#E8F4FD', fg='#2C3E50').grid(row=1, column=2, padx=5, pady=5, sticky='e')
server_entry = tk.Entry(inner_conn_frame, width=15)
server_entry.insert(0, "localhost")
server_entry.grid(row=1, column=3, padx=5, pady=5)

tk.Label(inner_conn_frame, text="Port:", bg='#E8F4FD', fg='#2C3E50').grid(row=1, column=4, padx=5, pady=5, sticky='e')
port_entry = tk.Entry(inner_conn_frame, width=10)
port_entry.insert(0, "7520")
port_entry.grid(row=1, column=5, padx=5, pady=5)

# Connection buttons 
button_frame = tk.Frame(inner_conn_frame, bg='#E8F4FD')
button_frame.grid(row=2, column=0, columnspan=6, pady=5)

connect_button = tk.Button(button_frame, text="Connect", command=connect, bg='#3498DB', fg='black', width=12, font=('Arial', 9, 'bold'),activebackground='#2980B9', activeforeground='white')
connect_button.pack(side=tk.LEFT, padx=5)

disconnect_button = tk.Button(button_frame, text="Disconnect", command=disconnect, bg='#E74C3C', fg='black', width=12, state=tk.DISABLED, font=('Arial', 9, 'bold'),activebackground='#C0392B', activeforeground='white')
disconnect_button.pack(side=tk.LEFT, padx=5)

# Status label
status_label = tk.Label(inner_conn_frame, text="Status: Not Connected", fg="#E74C3C", bg='#E8F4FD', font=('Arial', 9, 'italic'))
status_label.grid(row=3, column=0, columnspan=6, pady=5)

# Middle section - File submission and lexicon
middle_frame = tk.Frame(main_container, bg='#E8F4FD')
middle_frame.pack(fill=tk.BOTH, expand=True)

# Left side - File submission
file_frame = tk.Frame(middle_frame, bg='#E8F4FD', relief=tk.RAISED, bd=2)
file_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

file_label = tk.Label(file_frame, text="FILE SUBMISSION", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
file_label.pack(pady=5)

file_input_frame = tk.Frame(file_frame, bg='#E8F4FD')
file_input_frame.pack(pady=5)

tk.Label(file_input_frame, text="Filename:", bg='#E8F4FD', fg='#2C3E50').pack(side=tk.LEFT, padx=5)
filename_entry = tk.Entry(file_input_frame, width=25)
filename_entry.pack(side=tk.LEFT, padx=5)

submit_button = tk.Button(file_frame, text="Submit File", command=submit_file, bg='#52BE80', fg='black', state=tk.DISABLED, font=('Arial', 9, 'bold'),activebackground='#27AE60', activeforeground='white')
submit_button.pack(pady=5)

# Right side - Lexicon management
lexicon_frame = tk.Frame(middle_frame, bg='#E8F4FD', relief=tk.RAISED, bd=2)
lexicon_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

lexicon_label = tk.Label(lexicon_frame, text="LEXICON MANAGEMENT", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
lexicon_label.pack(pady=5)

lexicon_input_frame = tk.Frame(lexicon_frame, bg='#E8F4FD')
lexicon_input_frame.pack(pady=5)

tk.Label(lexicon_input_frame, text="Add Word:", bg='#E8F4FD', fg='#2C3E50').pack(side=tk.LEFT, padx=5)
lexicon_entry = tk.Entry(lexicon_input_frame, width=25)
lexicon_entry.pack(side=tk.LEFT, padx=5)

add_word_button = tk.Button(lexicon_frame, text="Add to Lexicon", command=add_words, bg='#F39C12', fg='black', state=tk.DISABLED, font=('Arial', 9, 'bold'),activebackground='#E67E22', activeforeground='white')
add_word_button.pack(pady=5)

# Lexicon listbox
lexicon_listbox = tk.Listbox(lexicon_frame, height=6, width=35, bg='#FFFACD', fg='#2C3E50',  font=('Arial', 9, 'bold'),selectbackground='#3498DB',selectforeground='white')
lexicon_listbox.pack(pady=5, padx=10)

# Bottom section - Activity log
log_frame = tk.Frame(main_container, bg='#E8F4FD', relief=tk.RAISED, bd=2)
log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

log_label = tk.Label(log_frame, text="ACTIVITY LOG", font=('Arial', 10, 'bold'), bg='#E8F4FD', fg='#2C3E50')
log_label.pack(pady=5)

# Message area with scrollbar
msg_frame = tk.Frame(log_frame, bg='#E8F4FD')
msg_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(msg_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

msg = tk.Listbox(msg_frame, height=15, width=100, yscrollcommand=scrollbar.set, bg='white', fg='#2C3E50', font=('Courier', 9))
msg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=msg.yview)

# Initial message
msg.insert(tk.END, "=" * 60)
msg.insert(tk.END, "DISTRIBUTED SPELL CHECKER CLIENT")
msg.insert(tk.END, "Ready to connect to spell check servers")
msg.insert(tk.END, "Default connection: localhost:7520 (Load Balancer)")
msg.insert(tk.END, "=" * 60)

# Run GUI
window.mainloop()