"""
Master Control Panel for Distributed Spell Checker
Central monitoring and control of all components
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import time
import socket

class MasterControlPanel:
    def __init__(self):
        self.processes = {}
        self.component_status = {
            'Server 1 (7530)': 'Stopped',
            'Server 2 (7531)': 'Stopped',
            'Load Balancer (7520)': 'Stopped',
            'Cache Manager': 'N/A',
            'Sync Manager': 'N/A'
        }
        
        self.setup_gui()
        
    def setup_gui(self):
        self.window = tk.Tk()
        self.window.title("DISTRIBUTED SPELL CHECKER - MASTER CONTROL")
        self.window.configure(bg='#2C3E50')
        self.window.geometry("1200x700")
        
        # Title
        title_frame = tk.Frame(self.window, bg='#34495E', relief=tk.RAISED, bd=2)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(title_frame, text="MASTER CONTROL PANEL", 
                font=('Arial', 16, 'bold'), bg='#34495E', fg='#ECF0F1').pack(pady=10)
        
        # Main container
        main_frame = tk.Frame(self.window, bg='#2C3E50')
        main_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        # Left - Component control
        control_frame = tk.Frame(main_frame, bg='#34495E', relief=tk.RAISED, bd=2)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(control_frame, text="COMPONENT CONTROL", font=('Arial', 12, 'bold'), 
                bg='#34495E', fg='white').pack(pady=10)
        
        # Component buttons
        components_container = tk.Frame(control_frame, bg='#34495E')
        components_container.pack(expand=True)
        
        # Server 1
        server1_frame = tk.Frame(components_container, bg='#34495E')
        server1_frame.pack(pady=5)
        tk.Label(server1_frame, text="Server 1:", bg='#34495E', fg='white', 
                width=15, anchor='e').pack(side=tk.LEFT, padx=5)
        self.server1_status = tk.Label(server1_frame, text="STOPPED", bg='#E74C3C', 
                                      fg='white', width=10)
        self.server1_status.pack(side=tk.LEFT, padx=5)
        self.server1_start_btn = tk.Button(server1_frame, text="Start", command=lambda: self.start_component('server1'),
                 bg='#27AE60', fg='black', width=8, font=('Arial', 9, 'bold'),
                 activebackground='#2ECC71', activeforeground='black')
        self.server1_start_btn.pack(side=tk.LEFT, padx=2)
        self.server1_stop_btn = tk.Button(server1_frame, text="Stop", command=lambda: self.stop_component('server1'),
                 bg='#E74C3C', fg='black', width=8, font=('Arial', 9, 'bold'),
                 activebackground='#C0392B', activeforeground='black', state=tk.DISABLED)
        self.server1_stop_btn.pack(side=tk.LEFT, padx=2)
        
        # Server 2
        server2_frame = tk.Frame(components_container, bg='#34495E')
        server2_frame.pack(pady=5)
        tk.Label(server2_frame, text="Server 2:", bg='#34495E', fg='white', 
                width=15, anchor='e').pack(side=tk.LEFT, padx=5)
        self.server2_status = tk.Label(server2_frame, text="STOPPED", bg='#E74C3C', 
                                      fg='white', width=10)
        self.server2_status.pack(side=tk.LEFT, padx=5)
        self.server2_start_btn = tk.Button(server2_frame, text="Start", command=lambda: self.start_component('server2'),
                 bg='#27AE60', fg='black', width=8, font=('Arial', 9, 'bold'),
                 activebackground='#2ECC71', activeforeground='black')
        self.server2_start_btn.pack(side=tk.LEFT, padx=2)
        self.server2_stop_btn = tk.Button(server2_frame, text="Stop", command=lambda: self.stop_component('server2'),
                 bg='#E74C3C', fg='black', width=8, font=('Arial', 9, 'bold'),
                 activebackground='#C0392B', activeforeground='black', state=tk.DISABLED)
        self.server2_stop_btn.pack(side=tk.LEFT, padx=2)
        
        # Load Balancer
        lb_frame = tk.Frame(components_container, bg='#34495E')
        lb_frame.pack(pady=5)
        tk.Label(lb_frame, text="Load Balancer:", bg='#34495E', fg='white', 
                width=15, anchor='e').pack(side=tk.LEFT, padx=5)
        self.lb_status = tk.Label(lb_frame, text="STOPPED", bg='#E74C3C', 
                                 fg='white', width=10)
        self.lb_status.pack(side=tk.LEFT, padx=5)
        self.lb_start_btn = tk.Button(lb_frame, text="Start", command=lambda: self.start_component('loadbalancer'),
                 bg='#27AE60', fg='black', width=8, font=('Arial', 9, 'bold'),
                 activebackground='#2ECC71', activeforeground='black')
        self.lb_start_btn.pack(side=tk.LEFT, padx=2)
        self.lb_stop_btn = tk.Button(lb_frame, text="Stop", command=lambda: self.stop_component('loadbalancer'),
                 bg='#E74C3C', fg='black', width=8, font=('Arial', 9, 'bold'),
                 activebackground='#C0392B', activeforeground='black', state=tk.DISABLED)
        self.lb_stop_btn.pack(side=tk.LEFT, padx=2)
        
        # Master controls - WITH PROPER STATE MANAGEMENT
        master_frame = tk.Frame(control_frame, bg='#34495E')
        master_frame.pack(pady=20)
        
        self.start_all_btn = tk.Button(master_frame, text="START ALL", command=self.start_all,
                 bg='#27AE60', fg='black', font=('Arial', 10, 'bold'),
                 width=12, height=2,
                 activebackground='#2ECC71', activeforeground='black')
        self.start_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_all_btn = tk.Button(master_frame, text="STOP ALL", command=self.stop_all,
                 bg='#E74C3C', fg='black', font=('Arial', 10, 'bold'),
                 width=12, height=2, state=tk.DISABLED,
                 activebackground='#C0392B', activeforeground='black')
        self.stop_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Right - System overview
        overview_frame = tk.Frame(main_frame, bg='#34495E', relief=tk.RAISED, bd=2)
        overview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(overview_frame, text="SYSTEM OVERVIEW", font=('Arial', 12, 'bold'), 
                bg='#34495E', fg='white').pack(pady=10)
        
        # Stats display
        stats_frame = tk.Frame(overview_frame, bg='#34495E')
        stats_frame.pack(pady=10)
        
        self.total_clients_label = tk.Label(stats_frame, text="Total Clients: 0", 
                                           bg='#34495E', fg='white', font=('Arial', 10))
        self.total_clients_label.grid(row=0, column=0, padx=20, pady=5)
        
        self.active_servers_label = tk.Label(stats_frame, text="Active Servers: 0/2", 
                                            bg='#34495E', fg='white', font=('Arial', 10))
        self.active_servers_label.grid(row=0, column=1, padx=20, pady=5)
        
        self.lb_status_label = tk.Label(stats_frame, text="Load Balancer: Inactive", 
                                       bg='#34495E', fg='white', font=('Arial', 10))
        self.lb_status_label.grid(row=1, column=0, padx=20, pady=5)
        
        self.uptime_label = tk.Label(stats_frame, text="System Uptime: 0s", 
                                    bg='#34495E', fg='white', font=('Arial', 10))
        self.uptime_label.grid(row=1, column=1, padx=20, pady=5)
        
        # Activity log
        log_frame = tk.Frame(overview_frame, bg='#34495E')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(log_frame, text="SYSTEM LOG", font=('Arial', 10, 'bold'), 
                bg='#34495E', fg='white').pack()
        
        log_container = tk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_container, height=15, width=50, 
                               bg='#ECF0F1', fg='#2C3E50', font=('Courier', 9),
                               yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Quick actions - FIXED BUTTON COLORS
        actions_frame = tk.Frame(self.window, bg='#34495E', relief=tk.RAISED, bd=2)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(actions_frame, text="QUICK ACTIONS:", bg='#34495E', fg='white',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)
        
        tk.Button(actions_frame, text="Launch Client", command=self.launch_client,
                 bg='#3498DB', fg='black', font=('Arial', 9, 'bold'),
                 activebackground='#2980B9', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(actions_frame, text="Test Connectivity", command=self.test_connectivity,
                 bg='#9B59B6', fg='black', font=('Arial', 9, 'bold'),
                 activebackground='#8E44AD', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # tk.Button(actions_frame, text="View Cache Stats", command=self.view_cache,
        #          bg='#16A085', fg='black', font=('Arial', 9, 'bold'),
        #          activebackground='#138D75', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # tk.Button(actions_frame, text="View Sync Status", command=self.view_sync,
        #          bg='#E67E22', fg='black', font=('Arial', 9, 'bold'),
        #          activebackground='#D35400', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Start monitoring
        self.start_time = time.time()
        self.start_monitoring()
        
    def update_button_states(self):
        """Update button states based on what's currently running"""
        # Count active components
        active_count = len(self.processes)
        server1_running = 'server1' in self.processes
        server2_running = 'server2' in self.processes
        lb_running = 'loadbalancer' in self.processes
        
        # Update individual component buttons
        if server1_running:
            self.server1_start_btn.config(state=tk.DISABLED)
            self.server1_stop_btn.config(state=tk.NORMAL)
        else:
            self.server1_start_btn.config(state=tk.NORMAL)
            self.server1_stop_btn.config(state=tk.DISABLED)
            
        if server2_running:
            self.server2_start_btn.config(state=tk.DISABLED)
            self.server2_stop_btn.config(state=tk.NORMAL)
        else:
            self.server2_start_btn.config(state=tk.NORMAL)
            self.server2_stop_btn.config(state=tk.DISABLED)
            
        if lb_running:
            self.lb_start_btn.config(state=tk.DISABLED)
            self.lb_stop_btn.config(state=tk.NORMAL)
        else:
            self.lb_start_btn.config(state=tk.NORMAL)
            self.lb_stop_btn.config(state=tk.DISABLED)
        
        # Update master control buttons
        all_core_running = server1_running and server2_running and lb_running
        
        if all_core_running:
            # All components running - disable START ALL, enable STOP ALL
            self.start_all_btn.config(state=tk.DISABLED, text="ALL RUNNING")
            self.stop_all_btn.config(state=tk.NORMAL)
        elif active_count > 0:
            # Some components running - enable both buttons
            self.start_all_btn.config(state=tk.NORMAL, text="START ALL")
            self.stop_all_btn.config(state=tk.NORMAL)
        else:
            # Nothing running - enable START ALL, disable STOP ALL
            self.start_all_btn.config(state=tk.NORMAL, text="START ALL")
            self.stop_all_btn.config(state=tk.DISABLED)
        
    def log(self, message):
        """Add message to log"""
        timestamp = time.strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def start_component(self, component):
        """Start a specific component"""
        if component == 'server1':
            cmd = "python3 server.py --port 7530"
            self.processes['server1'] = subprocess.Popen(cmd, shell=True)
            self.server1_status.config(text="RUNNING", bg='#27AE60')
            self.log("Started Server 1 on port 7530")
            
        elif component == 'server2':
            cmd = "python3 server.py --port 7531"
            self.processes['server2'] = subprocess.Popen(cmd, shell=True)
            self.server2_status.config(text="RUNNING", bg='#27AE60')
            self.log("Started Server 2 on port 7531")
            
        elif component == 'loadbalancer':
            cmd = "python3 load_balancer.py"
            self.processes['loadbalancer'] = subprocess.Popen(cmd, shell=True)
            self.lb_status.config(text="RUNNING", bg='#27AE60')
            self.log("Started Load Balancer on port 7520")
        
        # Update button states after starting component
        self.update_button_states()
            
    def stop_component(self, component):
        """Stop a specific component"""
        if component in self.processes:
            self.processes[component].terminate()
            del self.processes[component]
            
            if component == 'server1':
                self.server1_status.config(text="STOPPED", bg='#E74C3C')
                self.log("Stopped Server 1")
            elif component == 'server2':
                self.server2_status.config(text="STOPPED", bg='#E74C3C')
                self.log("Stopped Server 2")
            elif component == 'loadbalancer':
                self.lb_status.config(text="STOPPED", bg='#E74C3C')
                self.log("Stopped Load Balancer")
        
        # Update button states after stopping component
        self.update_button_states()
                
    def start_all(self):
        """Start all components"""
        self.log("Starting all components...")
        
        # Only start components that aren't already running
        if 'server1' not in self.processes:
            self.start_component('server1')
            time.sleep(1)
        
        if 'server2' not in self.processes:
            self.start_component('server2')
            time.sleep(1)
            
        if 'loadbalancer' not in self.processes:
            self.start_component('loadbalancer')
        
        self.log("Start all completed")
        
    def stop_all(self):
        """Stop all components"""
        self.log("Stopping all components...")
        for component in list(self.processes.keys()):
            self.stop_component(component)
        self.log("All components stopped")
        
    def launch_client(self):
        """Launch a client instance"""
        subprocess.Popen("python3 client.py", shell=True)
        self.log("Launched new client instance")
        
    def test_connectivity(self):
        """Test system connectivity"""
        subprocess.Popen("python3 test_system.py", shell=True)
        self.log("Running connectivity test...")
        
    def view_cache(self):
        """Cache is now backend only - show message"""
        self.log("Cache is integrated into servers - check server logs for cache hits/misses")
        
    def view_sync(self):
        """Sync is now backend only - show message"""
        self.log("Sync is integrated into servers - lexicon updates are automatically synchronized")
        
    def start_monitoring(self):
        """Monitor system status"""
        def monitor():
            while True:
                # Update uptime
                uptime = int(time.time() - self.start_time)
                self.uptime_label.config(text=f"System Uptime: {uptime}s")
                
                # Check component status and update button states
                active_servers = 0
                if 'server1' in self.processes:
                    active_servers += 1
                if 'server2' in self.processes:
                    active_servers += 1
                    
                self.active_servers_label.config(text=f"Active Servers: {active_servers}/2")
                
                if 'loadbalancer' in self.processes:
                    self.lb_status_label.config(text="Load Balancer: Active")
                else:
                    self.lb_status_label.config(text="Load Balancer: Inactive")
                
                # Update button states based on current status
                self.update_button_states()
                    
                time.sleep(1)
                
        threading.Thread(target=monitor, daemon=True).start()
        
    def start(self):
        """Start the control panel"""
        self.log("Master Control Panel initialized")
        self.log("Ready to manage distributed spell checker system")
        # Initialize button states
        self.update_button_states()
        self.window.mainloop()

if __name__ == "__main__":
    panel = MasterControlPanel()
    panel.start()