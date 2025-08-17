import serial
import serial.tools.list_ports
import time
import matplotlib.pyplot as plt
import json
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import numpy as np

class SmartIrrigationMonitor:
    def __init__(self, port='COM6', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_connected = False
        self.total_water_used = 0.0
        
        # Current irrigation data
        self.current_moisture = 0
        self.pump_status = False
        self.total_water_used_today = 0.0
        self.watering_events_today = 0
        self.last_timestamp = None
        
        # Thresholds - Updated to match Arduino's digital sensor logic
        self.dry_threshold = 700   # Value when soil is dry (Arduino sends 700 for LOW/dry)
        self.wet_threshold = 300   # Value when soil is wet (Arduino sends 300 for HIGH/wet)
        self.flow_rate = 1.0  # liters per minute
        
        # Historical data storage with time aggregations
        self.minute_data = defaultdict(lambda: {
            'water_used': 0.0, 'moisture': 0, 'events': 0, 'pump_duration': 0.0
        })
        self.hourly_data = defaultdict(lambda: {
            'water_used': 0.0, 'moisture': 0, 'events': 0, 'pump_duration': 0.0
        })
        self.daily_data = defaultdict(lambda: {
            'water_used': 0.0, 'moisture_avg': 0, 'events': 0, 'pump_duration': 0.0
        })
        self.monthly_data = defaultdict(lambda: {
            'water_used': 0.0, 'moisture_avg': 0, 'events': 0, 'pump_duration': 0.0
        })
        self.yearly_data = defaultdict(lambda: {
            'water_used': 0.0, 'moisture_avg': 0, 'events': 0, 'pump_duration': 0.0
        })
        
        self.recent_activity = deque(maxlen=100)
        
        # Data files for persistence
        self.data_file = 'irrigation_data.json'
        self.csv_file = 'irrigation_data.csv'
        self.load_historical_data()
        
        # GUI setup
        self.setup_gui()
        
        # Scan for available ports on startup
        self.scan_ports()
        
        # Start monitoring thread
        self.monitoring_thread = None
        self.monitoring_active = False
        
    def setup_gui(self):
        """Create the irrigation dashboard with tabbed interface"""
        self.root = tk.Tk()
        self.root.title("Smart Irrigation System Dashboard")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2c3e50')
        
        # Main title
        title_label = tk.Label(self.root, text="💧 SMART IRRIGATION DASHBOARD", 
                              font=('Arial', 20, 'bold'), 
                              fg='white', bg='#2c3e50')
        title_label.pack(pady=10)
        
        # Connection status frame
        conn_frame = tk.Frame(self.root, bg='#2c3e50')
        conn_frame.pack(pady=5)
        
        self.conn_status_label = tk.Label(conn_frame, text="⚫ Disconnected", 
                                         font=('Arial', 12), 
                                         fg='red', bg='#2c3e50')
        self.conn_status_label.pack(side=tk.LEFT)
        
        # Port selection dropdown
        tk.Label(conn_frame, text="Port:", fg='white', bg='#2c3e50',
                font=('Arial', 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        self.port_var = tk.StringVar(value=self.port)
        self.port_dropdown = ttk.Combobox(conn_frame, textvariable=self.port_var,
                                         width=8, state="readonly")
        self.port_dropdown.pack(side=tk.LEFT, padx=5)
        
        tk.Button(conn_frame, text="🔍 Scan", command=self.scan_ports,
                 bg='#f39c12', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", 
                                    command=self.toggle_connection,
                                    bg='#3498db', fg='white', 
                                    font=('Arial', 10))
        self.connect_btn.pack(side=tk.LEFT, padx=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Create tabs
        self.create_current_status_tab()
        self.create_recent_activity_tab()
        self.create_graphs_tab()
        self.create_export_tab()
        
    def create_current_status_tab(self):
        """Create Current Status tab"""
        self.status_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.status_frame, text="Current Status")
        
        # Current Status Section
        status_info_frame = tk.LabelFrame(self.status_frame, text="Real-time Status", 
                                         font=('Arial', 14, 'bold'),
                                         fg='white', bg='#34495e')
        status_info_frame.pack(pady=10, padx=20, fill='x')
        
        # Current time display
        self.time_label = tk.Label(status_info_frame, 
                                  text="Last Update: Not connected",
                                  font=('Arial', 12),
                                  fg='#ecf0f1', bg='#34495e')
        self.time_label.pack(pady=5)
        
        # Moisture level display
        self.moisture_label = tk.Label(status_info_frame, 
                                     text=f"Soil Moisture: {self.current_moisture}",
                                     font=('Arial', 14),
                                     fg='white', bg='#34495e')
        self.moisture_label.pack(pady=5)
        
        # Moisture status indicator
        self.moisture_status = tk.Label(status_info_frame, 
                                       text="Status: UNKNOWN",
                                       font=('Arial', 12, 'bold'),
                                       bg='#34495e')
        self.moisture_status.pack(pady=5)
        
        # Pump status
        self.pump_label = tk.Label(status_info_frame, 
                                 text="Pump: INACTIVE",
                                 font=('Arial', 12),
                                 fg='white', bg='#34495e')
        self.pump_label.pack(pady=5)
        
        # Today's Statistics Section
        today_frame = tk.LabelFrame(self.status_frame, text="Today's Statistics", 
                                  font=('Arial', 14, 'bold'),
                                  fg='white', bg='#34495e')
        today_frame.pack(pady=10, padx=20, fill='x')
        
        stats_inner_frame = tk.Frame(today_frame, bg='#34495e')
        stats_inner_frame.pack(pady=10)
        
        self.water_used_label = tk.Label(stats_inner_frame, 
                                       text=f"Water Used: {self.total_water_used_today:.2f} L",
                                       font=('Arial', 12),
                                       fg='#27ae60', bg='#34495e')
        self.water_used_label.grid(row=0, column=0, padx=20)
        
        self.events_label = tk.Label(stats_inner_frame, 
                                   text=f"Watering Events: {self.watering_events_today}",
                                   font=('Arial', 12),
                                   fg='#f39c12', bg='#34495e')
        self.events_label.grid(row=0, column=1, padx=20)
        
        self.total_label = tk.Label(stats_inner_frame, 
                          text=f"Lifetime Total: {self.total_water_used:.2f} L",
                          font=('Arial', 12),
                          fg='#3498db', bg='#34495e')
        self.total_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Control buttons
        control_frame = tk.Frame(self.status_frame, bg='#2c3e50')
        control_frame.pack(pady=20)
        
        tk.Button(control_frame, text="🔄 Refresh", 
                 command=self.refresh_dashboard,
                 bg='#2ecc71', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="⚙️ Settings", 
                 command=self.show_settings,
                 bg='#3498db', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    def create_recent_activity_tab(self):
        """Create Recent Activity tab"""
        self.activity_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.activity_frame, text="Recent Activity")
        
        # Activity listbox with scrollbar
        listbox_frame = tk.Frame(self.activity_frame, bg='#34495e')
        listbox_frame.pack(fill='both', expand=True, pady=10, padx=10)
        
        self.activity_listbox = tk.Listbox(listbox_frame, 
                                         font=('Arial', 10),
                                         bg='#2c3e50', fg='white',
                                         selectbackground='#3498db')
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.activity_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        
        self.activity_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.activity_listbox.yview)
        
        # Clear activity button
        tk.Button(self.activity_frame, text="Clear Activity Log", 
                 command=self.clear_activity,
                 bg='#e74c3c', fg='white', 
                 font=('Arial', 10)).pack(pady=5)
    
    def create_graphs_tab(self):
        """Create Graphs tab"""
        self.graphs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.graphs_frame, text="Graphs & Analytics")
        
        # Graph control frame
        graph_control_frame = tk.LabelFrame(self.graphs_frame, text="Data Visualization", 
                                          font=('Arial', 12, 'bold'))
        graph_control_frame.pack(pady=10, padx=20, fill='x')
        
        # Water usage graphs
        water_frame = tk.Frame(graph_control_frame)
        water_frame.pack(pady=5, fill='x')
        
        tk.Label(water_frame, text="Water Usage:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(water_frame, text="📊 Minute", 
                 command=lambda: self.show_water_usage_graph('minute'),
                 bg='#9b59b6', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(water_frame, text="📊 Hourly", 
                 command=lambda: self.show_water_usage_graph('hour'),
                 bg='#9b59b6', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(water_frame, text="📊 Daily", 
                 command=lambda: self.show_water_usage_graph('day'),
                 bg='#9b59b6', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(water_frame, text="📊 Monthly", 
                 command=lambda: self.show_water_usage_graph('month'),
                 bg='#9b59b6', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(water_frame, text="📊 Yearly", 
                 command=lambda: self.show_water_usage_graph('year'),
                 bg='#9b59b6', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        # Moisture graphs
        moisture_frame = tk.Frame(graph_control_frame)
        moisture_frame.pack(pady=5, fill='x')
        
        tk.Label(moisture_frame, text="Moisture Levels:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(moisture_frame, text="📈 Minute", 
                 command=lambda: self.show_moisture_graph('minute'),
                 bg='#e67e22', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(moisture_frame, text="📈 Hourly", 
                 command=lambda: self.show_moisture_graph('hour'),
                 bg='#e67e22', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(moisture_frame, text="📈 Daily", 
                 command=lambda: self.show_moisture_graph('day'),
                 bg='#e67e22', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        # Combined analysis
        analysis_frame = tk.Frame(graph_control_frame)
        analysis_frame.pack(pady=5, fill='x')
        
        tk.Label(analysis_frame, text="Analysis:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(analysis_frame, text="🔍 Efficiency Analysis", 
                 command=self.show_efficiency_analysis,
                 bg='#16a085', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(analysis_frame, text="📊 Pump Duration Analysis", 
                 command=self.show_pump_duration_analysis,
                 bg='#8e44ad', fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
    
    def create_export_tab(self):
        """Create Export tab"""
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="Export & Data")
        
        # Export control frame
        export_control_frame = tk.LabelFrame(self.export_frame, text="Data Export Options", 
                                           font=('Arial', 12, 'bold'))
        export_control_frame.pack(pady=10, padx=20, fill='x')
        
        # JSON Export
        json_frame = tk.Frame(export_control_frame)
        json_frame.pack(pady=5, fill='x')
        
        tk.Button(json_frame, text="💾 Export JSON", 
                 command=self.export_json_data,
                 bg='#16a085', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(json_frame, text="Export all data in JSON format").pack(side=tk.LEFT, padx=10)
        
        # CSV Export
        csv_frame = tk.Frame(export_control_frame)
        csv_frame.pack(pady=5, fill='x')
        
        tk.Button(csv_frame, text="📊 Export CSV", 
                 command=self.export_csv_data,
                 bg='#27ae60', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(csv_frame, text="Export data in CSV format for Excel").pack(side=tk.LEFT, padx=10)
        
        # Data summary frame
        summary_frame = tk.LabelFrame(self.export_frame, text="Data Summary", 
                                    font=('Arial', 12, 'bold'))
        summary_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        self.summary_text = tk.Text(summary_frame, height=15, width=60,
                                   bg='#34495e', fg='white', font=('Arial', 10))
        summary_scrollbar = tk.Scrollbar(summary_frame)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.pack(side=tk.LEFT, fill='both', expand=True)
        self.summary_text.config(yscrollcommand=summary_scrollbar.set)
        summary_scrollbar.config(command=self.summary_text.yview)
        
        # Update summary button
        tk.Button(self.export_frame, text="🔄 Update Summary", 
                 command=self.update_data_summary,
                 bg='#3498db', fg='white', 
                 font=('Arial', 10)).pack(pady=5)
    
    def scan_ports(self):
        """Scan for available serial ports"""
        ports = serial.tools.list_ports.comports()
        available_ports = []
        
        for port in ports:
            available_ports.append(port.device)
        
        if available_ports:
            self.port_dropdown['values'] = available_ports
            if self.port not in available_ports and available_ports:
                self.port = available_ports[0]
                self.port_var.set(self.port)
            self.add_activity(f"🔍 Found {len(available_ports)} serial ports")
        else:
            self.port_dropdown['values'] = []
            self.add_activity("⚠️ No serial ports detected")
    
    def toggle_connection(self):
        """Toggle Arduino connection"""
        # Update port from dropdown selection
        self.port = self.port_var.get()
        
        if not self.port:
            messagebox.showerror("Port Error", "Please select a COM port first")
            return
            
        if not self.is_connected:
            self.connect_to_arduino()
        else:
            self.disconnect_arduino()
    
    def connect_to_arduino(self):
        """Establish connection with Arduino"""
        try:
            self.add_activity(f"🔌 Attempting to connect to {self.port}...")
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(3)  # Wait for Arduino to reset
            
            # Test if we can communicate
            test_successful = False
            start_time = time.time()
            
            while time.time() - start_time < 5:  # Wait up to 5 seconds for data
                if self.serial_connection.in_waiting > 0:
                    test_line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if test_line:
                        test_successful = True
                        break
                time.sleep(0.1)
            
            if test_successful:
                self.is_connected = True
                self.conn_status_label.config(text="🟢 Connected", fg='green')
                self.connect_btn.config(text="Disconnect")
                
                self.monitoring_active = True
                self.monitoring_thread = threading.Thread(target=self.monitor_arduino, daemon=True)
                self.monitoring_thread.start()
                
                self.add_activity(f"✅ Connected to Arduino on {self.port}")
            else:
                self.serial_connection.close()
                raise Exception("No data received from Arduino. Check if your Arduino code is running.")
            
        except serial.SerialException as e:
            error_msg = f"Serial connection failed: {str(e)}"
            if "Access is denied" in str(e):
                error_msg += "\n\nTroubleshooting:\n• Close Arduino IDE if open\n• Try a different USB port\n• Check if another program is using the port"
            elif "could not open port" in str(e):
                error_msg += "\n\nTroubleshooting:\n• Verify Arduino is connected\n• Check USB cable\n• Try scanning for ports again"
            
            messagebox.showerror("Connection Error", error_msg)
            self.add_activity(f"❌ Connection failed: {str(e)}")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.add_activity(f"❌ Connection error: {str(e)}")
    
    def disconnect_arduino(self):
        """Disconnect from Arduino"""
        self.monitoring_active = False
        if self.serial_connection:
            self.serial_connection.close()
        self.is_connected = False
        self.conn_status_label.config(text="⚫ Disconnected", fg='red')
        self.connect_btn.config(text="Connect")
        self.add_activity("❌ Disconnected from Arduino")
    
    def monitor_arduino(self):
        """Monitor Arduino data in separate thread"""
        while self.monitoring_active and self.is_connected:
            try:
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    self.process_arduino_data(line)
                time.sleep(0.1)
            except Exception as e:
                print(f"Monitoring error: {e}")
                self.root.after(0, self.disconnect_arduino)
                break
    
    def process_arduino_data(self, data):
        """Process incoming Arduino data"""
        if data.startswith("IRRIGATION_DATA:"):
            try:
                # Debug: show raw data
                self.add_activity(f"🔍 Raw data: {data}")
                
                data_part = data.replace("IRRIGATION_DATA:", "")
                params = {}
                for param in data_part.split(","):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        if key == "MOISTURE":
                            params[key] = int(value)
                        elif key == "PUMP":
                            params[key] = bool(int(value))
                        elif key in ["WATER_USED", "TOTAL"]:
                            params[key] = float(value)
                        elif key == "EVENTS":
                            params[key] = int(value)
                        elif key == "TIME":
                            params[key] = value
                
                # Update current data
                self.current_moisture = params.get("MOISTURE", 0)
                self.pump_status = params.get("PUMP", False)
                self.total_water_used_today = params.get("WATER_USED", 0.0)
                self.watering_events_today = params.get("EVENTS", 0)
                self.total_water_used = params.get("TOTAL", 0.0)
                self.last_timestamp = params.get("TIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # Debug: show parsed values
                self.add_activity(
                    f"📊 Parsed - Moisture: {self.current_moisture}, Pump: {self.pump_status}, Sensor should be: {'DRY' if self.current_moisture >= 700 else 'WET'}"
                )
                
                self.update_aggregated_data()
                self.root.after(0, self.update_gui)
                
            except Exception as e:
                print(f"Data parsing error: {e}")
                self.add_activity(f"[ERROR] Bad data: {data}")
                self.add_activity(f"[ERROR] Parsing error: {str(e)}")
    
    def update_aggregated_data(self):
        """Update all time-aggregated data"""
        if not self.last_timestamp:
            return
            
        try:
            timestamp = datetime.strptime(self.last_timestamp, "%Y-%m-%d %H:%M:%S")
        except:
            timestamp = datetime.now()
        
        # Generate time keys for different aggregation levels
        minute_key = timestamp.strftime("%Y-%m-%d %H:%M")
        hour_key = timestamp.strftime("%Y-%m-%d %H:00")
        day_key = timestamp.strftime("%Y-%m-%d")
        month_key = timestamp.strftime("%Y-%m")
        year_key = timestamp.strftime("%Y")
        
        # Calculate pump duration (simplified - in real implementation you'd track actual duration)
        pump_duration = 2.0 if self.pump_status else 0.0  # 2 seconds per update when pump is on
        
        # Update minute data
        self.minute_data[minute_key].update({
            'water_used': self.total_water_used_today,
            'moisture': self.current_moisture,
            'events': self.watering_events_today,
            'pump_duration': self.minute_data[minute_key]['pump_duration'] + pump_duration
        })
        
        # Update hourly data
        self.hourly_data[hour_key].update({
            'water_used': self.total_water_used_today,
            'moisture': self.current_moisture,
            'events': self.watering_events_today,
            'pump_duration': self.hourly_data[hour_key]['pump_duration'] + pump_duration
        })
        
        # Update daily data
        self.daily_data[day_key].update({
            'water_used': self.total_water_used_today,
            'moisture_avg': self.current_moisture,
            'events': self.watering_events_today,
            'pump_duration': self.daily_data[day_key]['pump_duration'] + pump_duration
        })
        
        # Update monthly data (aggregate from daily)
        month_water = sum(day_data['water_used'] for day_key, day_data in self.daily_data.items() 
                         if day_key.startswith(month_key))
        month_events = sum(day_data['events'] for day_key, day_data in self.daily_data.items() 
                          if day_key.startswith(month_key))
        
        self.monthly_data[month_key].update({
            'water_used': month_water,
            'events': month_events,
            'pump_duration': self.monthly_data[month_key]['pump_duration'] + pump_duration
        })
        
        # Update yearly data (aggregate from monthly)
        year_water = sum(month_data['water_used'] for month_key, month_data in self.monthly_data.items() 
                        if month_key.startswith(year_key))
        year_events = sum(month_data['events'] for month_key, month_data in self.monthly_data.items() 
                         if month_key.startswith(year_key))
        
        self.yearly_data[year_key].update({
            'water_used': year_water,
            'events': year_events,
            'pump_duration': self.yearly_data[year_key]['pump_duration'] + pump_duration
        })
    
    def update_gui(self):
        """Update GUI elements with current data"""
        # Update current status
        self.moisture_label.config(text=f"Soil Moisture: {self.current_moisture}")
        
        if self.last_timestamp:
            self.time_label.config(text=f"Last Update: {self.last_timestamp}")
        
        # Update moisture status with color coding
        # Arduino sends: 700 when DRY (LOW reading), 300 when WET (HIGH reading)
        if self.current_moisture >= 700:  # DRY soil
            status = "DRY - Needs Water"
            color = '#e74c3c'  # Red
        elif self.current_moisture <= 300:  # WET soil
            status = "WET - Well Watered" 
            color = '#27ae60'  # Green
        else:
            status = "OPTIMAL - Good Moisture"
            color = '#f39c12'  # Orange
            
        self.moisture_status.config(text=f"Status: {status}", fg=color)
        
        # Update pump status
        self.pump_label.config(text=f"Pump: {'🟢 ACTIVE' if self.pump_status else '🔴 INACTIVE'}",
                             fg='#27ae60' if self.pump_status else '#e74c3c')
        
        # Update today's statistics
        self.water_used_label.config(text=f"Water Used: {self.total_water_used_today:.2f} L")
        self.events_label.config(text=f"Watering Events: {self.watering_events_today}")
        self.total_label.config(text=f"Lifetime Total: {self.total_water_used:.2f} L")
    
    def add_activity(self, message):
        """Add activity to the recent activity list"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        activity = f"[{timestamp}] {message}"
        self.recent_activity.append(activity)
        self.root.after(0, self.update_activity_listbox)
    
    def update_activity_listbox(self):
        """Update the activity listbox"""
        self.activity_listbox.delete(0, tk.END)
        for activity in reversed(list(self.recent_activity)):
            self.activity_listbox.insert(0, activity)
    
    def clear_activity(self):
        """Clear activity log"""
        self.recent_activity.clear()
        self.update_activity_listbox()
    
    def show_water_usage_graph(self, period):
        """Show water usage graph for specified period"""
        data_dict = {
            'minute': self.minute_data,
            'hour': self.hourly_data,
            'day': self.daily_data,
            'month': self.monthly_data,
            'year': self.yearly_data
        }
        
        data = data_dict.get(period, {})
        if not data:
            messagebox.showinfo("No Data", f"No {period}ly data available to display")
            return
        
        periods = sorted(data.keys())
        water_used = [data[period_key]['water_used'] for period_key in periods]
        events = [data[period_key]['events'] for period_key in periods]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Water usage graph
        ax1.bar(periods, water_used, color='#3498db', alpha=0.7, edgecolor='#2980b9')
        ax1.set_title(f'{period.title()}ly Water Usage', fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Water Used (Liters)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for i, v in enumerate(water_used):
            if v > 0:
                ax1.text(i, v + max(water_used) * 0.01, f'{v:.1f}L', 
                        ha='center', va='bottom', fontweight='bold')
        
        # Events graph
        ax2.bar(periods, events, color='#2ecc71', alpha=0.7, edgecolor='#27ae60')
        ax2.set_title(f'{period.title()}ly Watering Events', fontsize=16, fontweight='bold', pad=20)
        ax2.set_ylabel('Number of Events', fontsize=12)
        ax2.set_xlabel('Time Period', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for i, v in enumerate(events):
            if v > 0:
                ax2.text(i, v + max(events) * 0.01, str(v), 
                        ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
    
    def show_moisture_graph(self, period):
        """Show moisture graph for specified period"""
        data_dict = {
            'minute': self.minute_data,
            'hour': self.hourly_data,
            'day': self.daily_data
        }
        
        data = data_dict.get(period, {})
        if not data:
            messagebox.showinfo("No Data", f"No {period}ly moisture data available")
            return
        
        periods = sorted(data.keys())
        moisture_key = 'moisture' if period in ['minute', 'hour'] else 'moisture_avg'
        moisture = [data[period_key][moisture_key] for period_key in periods]
        
        plt.figure(figsize=(14, 8))
        
        # Plot moisture levels
        plt.plot(periods, moisture, marker='o', color='#9b59b6', 
                label='Moisture Level', linewidth=2, markersize=6)
        
        # Add threshold lines
        plt.axhline(y=self.dry_threshold, color='red', linestyle='--', linewidth=2,
                   label=f'Dry Threshold ({self.dry_threshold})')
        plt.axhline(y=self.wet_threshold, color='green', linestyle='--', linewidth=2,
                   label=f'Wet Threshold ({self.wet_threshold})')
        
        plt.title(f'{period.title()}ly Soil Moisture History', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Time Period', fontsize=12)
        plt.ylabel('Moisture Level', fontsize=12)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def show_efficiency_analysis(self):
        """Show irrigation efficiency analysis"""
        if not self.daily_data:
            messagebox.showinfo("No Data", "No daily data available for analysis")
            return
        
        # Calculate efficiency metrics
        dates = sorted(self.daily_data.keys())
        water_per_event = []
        efficiency_scores = []
        
        for date in dates:
            data = self.daily_data[date]
            events = data['events']
            water = data['water_used']
            
            if events > 0:
                wpe = water / events
                water_per_event.append(wpe)
                
                # Simple efficiency score (lower water per event = higher efficiency)
                # Normalize between 0-100
                max_wpe = 10.0  # Assume max 10L per event for normalization
                efficiency = max(0, 100 - (wpe / max_wpe * 100))
                efficiency_scores.append(efficiency)
            else:
                water_per_event.append(0)
                efficiency_scores.append(100)  # No watering needed = 100% efficient
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))
        
        # Water per event
        ax1.plot(dates, water_per_event, marker='s', color='#e74c3c', 
                linewidth=2, markersize=6, label='Water per Event')
        ax1.set_title('Water Usage per Watering Event', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Liters per Event')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Efficiency scores
        ax2.bar(dates, efficiency_scores, color='#27ae60', alpha=0.7)
        ax2.set_title('Daily Irrigation Efficiency Score', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Efficiency Score (%)')
        ax2.grid(True, alpha=0.3)
        
        # Cumulative water usage
        cumulative_water = []
        total = 0
        for date in dates:
            total += self.daily_data[date]['water_used']
            cumulative_water.append(total)
        
        ax3.plot(dates, cumulative_water, marker='o', color='#3498db', 
                linewidth=3, markersize=6, label='Cumulative Water Usage')
        ax3.fill_between(dates, cumulative_water, alpha=0.3, color='#3498db')
        ax3.set_title('Cumulative Water Usage Over Time', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Total Liters')
        ax3.set_xlabel('Date')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        for ax in [ax1, ax2, ax3]:
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def show_pump_duration_analysis(self):
        """Show pump duration analysis"""
        if not self.daily_data:
            messagebox.showinfo("No Data", "No daily data available for analysis")
            return
        
        dates = sorted(self.daily_data.keys())
        pump_durations = [self.daily_data[date]['pump_duration'] / 60.0 for date in dates]  # Convert to minutes
        water_used = [self.daily_data[date]['water_used'] for date in dates]
        events = [self.daily_data[date]['events'] for date in dates]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))
        
        # Daily pump duration
        ax1.bar(dates, pump_durations, color='#8e44ad', alpha=0.7)
        ax1.set_title('Daily Pump Duration', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Duration (minutes)')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Pump duration vs Water used
        ax2.scatter(pump_durations, water_used, color='#e67e22', s=60, alpha=0.7)
        ax2.set_title('Pump Duration vs Water Used', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Pump Duration (minutes)')
        ax2.set_ylabel('Water Used (Liters)')
        ax2.grid(True, alpha=0.3)
        
        # Add trend line
        if len(pump_durations) > 1:
            z = np.polyfit(pump_durations, water_used, 1)
            p = np.poly1d(z)
            ax2.plot(pump_durations, p(pump_durations), "r--", alpha=0.8)
        
        # Average duration per event
        avg_duration_per_event = []
        for i, date in enumerate(dates):
            if events[i] > 0:
                avg_duration_per_event.append(pump_durations[i] / events[i])
            else:
                avg_duration_per_event.append(0)
        
        ax3.plot(dates, avg_duration_per_event, marker='d', color='#16a085', 
                linewidth=2, markersize=6)
        ax3.set_title('Average Duration per Watering Event', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Minutes per Event')
        ax3.grid(True, alpha=0.3)
        ax3.tick_params(axis='x', rotation=45)
        
        # Pump efficiency (water/time)
        efficiency = []
        for i in range(len(dates)):
            if pump_durations[i] > 0:
                eff = water_used[i] / pump_durations[i]  # Liters per minute
                efficiency.append(eff)
            else:
                efficiency.append(0)
        
        ax4.bar(dates, efficiency, color='#f39c12', alpha=0.7)
        ax4.set_title('Pump Efficiency (L/min)', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Liters per Minute')
        ax4.set_xlabel('Date')
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def export_json_data(self):
        """Export all data to JSON file"""
        data = {
            'minute_data': dict(self.minute_data),
            'hourly_data': dict(self.hourly_data),
            'daily_data': dict(self.daily_data),
            'monthly_data': dict(self.monthly_data),
            'yearly_data': dict(self.yearly_data),
            'current_status': {
                'moisture': self.current_moisture,
                'pump_status': self.pump_status,
                'water_used_today': self.total_water_used_today,
                'events_today': self.watering_events_today,
                'total_water_used': self.total_water_used,
                'last_timestamp': self.last_timestamp
            },
            'settings': {
                'dry_threshold': self.dry_threshold,
                'wet_threshold': self.wet_threshold,
                'flow_rate': self.flow_rate
            },
            'export_timestamp': datetime.now().isoformat()
        }
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export JSON Data"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                messagebox.showinfo("Export Successful", f"Data exported to {filename}")
                self.add_activity(f"📁 Data exported to JSON: {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export JSON data: {str(e)}")
    
    def export_csv_data(self):
        """Export data to CSV files"""
        try:
            # Ask user to select directory
            directory = filedialog.askdirectory(title="Select Directory for CSV Export")
            if not directory:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export daily data
            if self.daily_data:
                daily_filename = os.path.join(directory, f"daily_irrigation_data_{timestamp}.csv")
                daily_df = pd.DataFrame([
                    {
                        'Date': date,
                        'Water_Used_L': data['water_used'],
                        'Watering_Events': data['events'],
                        'Avg_Moisture': data.get('moisture_avg', 0),
                        'Pump_Duration_Minutes': data.get('pump_duration', 0) / 60.0
                    }
                    for date, data in sorted(self.daily_data.items())
                ])
                daily_df.to_csv(daily_filename, index=False)
            
            # Export hourly data
            if self.hourly_data:
                hourly_filename = os.path.join(directory, f"hourly_irrigation_data_{timestamp}.csv")
                hourly_df = pd.DataFrame([
                    {
                        'DateTime': datetime_str,
                        'Water_Used_L': data['water_used'],
                        'Moisture_Level': data['moisture'],
                        'Watering_Events': data['events'],
                        'Pump_Duration_Seconds': data.get('pump_duration', 0)
                    }
                    for datetime_str, data in sorted(self.hourly_data.items())
                ])
                hourly_df.to_csv(hourly_filename, index=False)
            
            # Export monthly summary
            if self.monthly_data:
                monthly_filename = os.path.join(directory, f"monthly_irrigation_summary_{timestamp}.csv")
                monthly_df = pd.DataFrame([
                    {
                        'Month': month,
                        'Total_Water_Used_L': data['water_used'],
                        'Total_Events': data['events'],
                        'Total_Pump_Duration_Hours': data.get('pump_duration', 0) / 3600.0
                    }
                    for month, data in sorted(self.monthly_data.items())
                ])
                monthly_df.to_csv(monthly_filename, index=False)
            
            messagebox.showinfo("Export Successful", f"CSV files exported to {directory}")
            self.add_activity(f"📊 Data exported to CSV files in: {os.path.basename(directory)}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV data: {str(e)}")
    
    def update_data_summary(self):
        """Update the data summary display"""
        summary = []
        summary.append("=== SMART IRRIGATION SYSTEM DATA SUMMARY ===\n")
        summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        summary.append(f"Connection Status: {'Connected' if self.is_connected else 'Disconnected'}\n\n")
        
        # Current status
        summary.append("--- CURRENT STATUS ---")
        summary.append(f"Soil Moisture: {self.current_moisture}")
        summary.append(f"Pump Status: {'ACTIVE' if self.pump_status else 'INACTIVE'}")
        summary.append(f"Water Used Today: {self.total_water_used_today:.2f} L")
        summary.append(f"Events Today: {self.watering_events_today}")
        summary.append(f"Total Water Used: {self.total_water_used:.2f} L")
        if self.last_timestamp:
            summary.append(f"Last Update: {self.last_timestamp}")
        summary.append("")
        
        # Data availability
        summary.append("--- DATA AVAILABILITY ---")
        summary.append(f"Minute Records: {len(self.minute_data)}")
        summary.append(f"Hourly Records: {len(self.hourly_data)}")
        summary.append(f"Daily Records: {len(self.daily_data)}")
        summary.append(f"Monthly Records: {len(self.monthly_data)}")
        summary.append(f"Yearly Records: {len(self.yearly_data)}")
        summary.append("")
        
        # Recent daily statistics
        if self.daily_data:
            summary.append("--- RECENT DAILY STATISTICS ---")
            recent_days = sorted(self.daily_data.keys())[-7:]  # Last 7 days
            for day in recent_days:
                data = self.daily_data[day]
                summary.append(f"{day}: {data['water_used']:.1f}L, {data['events']} events")
            summary.append("")
        
        # Monthly totals
        if self.monthly_data:
            summary.append("--- MONTHLY TOTALS ---")
            for month in sorted(self.monthly_data.keys()):
                data = self.monthly_data[month]
                summary.append(f"{month}: {data['water_used']:.1f}L total, {data['events']} events")
            summary.append("")
        
        # System settings
        summary.append("--- SYSTEM SETTINGS ---")
        summary.append(f"Dry Threshold: {self.dry_threshold}")
        summary.append(f"Wet Threshold: {self.wet_threshold}")
        summary.append(f"Flow Rate: {self.flow_rate} L/min")
        summary.append("")
        
        # Calculate some statistics
        if self.daily_data:
            daily_values = [data['water_used'] for data in self.daily_data.values() if data['water_used'] > 0]
            if daily_values:
                summary.append("--- USAGE STATISTICS ---")
                summary.append(f"Average Daily Usage: {np.mean(daily_values):.2f} L")
                summary.append(f"Maximum Daily Usage: {max(daily_values):.2f} L")
                summary.append(f"Minimum Daily Usage: {min(daily_values):.2f} L")
                summary.append(f"Total Days with Usage: {len(daily_values)}")
        
        # Update the text widget
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, "\n".join(summary))
    
    def show_settings(self):
        """Show settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("System Settings")
        settings_window.geometry("450x350")
        settings_window.configure(bg='#34495e')
        
        # Settings frame
        main_frame = tk.Frame(settings_window, bg='#34495e')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Info label
        info_label = tk.Label(main_frame, 
                             text="Digital Moisture Sensor Values:\n• 700 = DRY soil (needs water)\n• 300 = WET soil (well watered)",
                             font=('Arial', 10), fg='#ecf0f1', bg='#34495e', justify='left')
        info_label.pack(pady=(0, 15))
        
        # Dry threshold setting  
        tk.Label(main_frame, text="Dry Threshold (when pump turns ON):", 
                font=('Arial', 12), fg='white', bg='#34495e').pack(pady=5)
        dry_spin = tk.Spinbox(main_frame, from_=0, to=1023, 
                             font=('Arial', 12), width=15)
        dry_spin.pack(pady=5)
        dry_spin.delete(0, tk.END)
        dry_spin.insert(0, str(self.dry_threshold))
        
        # Wet threshold setting
        tk.Label(main_frame, text="Wet Threshold (when pump turns OFF):", 
                font=('Arial', 12), fg='white', bg='#34495e').pack(pady=5)
        wet_spin = tk.Spinbox(main_frame, from_=0, to=1023, 
                            font=('Arial', 12), width=15)
        wet_spin.pack(pady=5)
        wet_spin.delete(0, tk.END)
        wet_spin.insert(0, str(self.wet_threshold))
        
        # Flow rate setting
        tk.Label(main_frame, text="Flow Rate (L/min):", 
                font=('Arial', 12), fg='white', bg='#34495e').pack(pady=5)
        flow_spin = tk.Spinbox(main_frame, from_=0.1, to=10.0, increment=0.1,
                             font=('Arial', 12), width=15)
        flow_spin.pack(pady=5)
        flow_spin.delete(0, tk.END)
        flow_spin.insert(0, f"{self.flow_rate:.1f}")
        
        # Connection settings
        tk.Label(main_frame, text="Arduino Port:", 
                font=('Arial', 12), fg='white', bg='#34495e').pack(pady=5)
        port_entry = tk.Entry(main_frame, font=('Arial', 12), width=15)
        port_entry.pack(pady=5)
        port_entry.insert(0, self.port)
        
        def save_settings():
            try:
                self.dry_threshold = int(dry_spin.get())
                self.wet_threshold = int(wet_spin.get())
                self.flow_rate = float(flow_spin.get())
                self.port = port_entry.get()
                
                if self.is_connected:
                    # Send new settings to Arduino (if your Arduino supports this)
                    settings_cmd = f"SETTINGS:DRY={self.dry_threshold},WET={self.wet_threshold},FLOW={self.flow_rate}\n"
                    try:
                        self.serial_connection.write(settings_cmd.encode())
                    except:
                        pass  # Settings command not implemented in Arduino
                
                messagebox.showinfo("Success", "Settings updated successfully!")
                settings_window.destroy()
                self.add_activity("⚙️ System settings updated")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid settings: {str(e)}")
        
        # Buttons frame
        button_frame = tk.Frame(main_frame, bg='#34495e')
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Save Settings", command=save_settings,
                 bg='#27ae60', fg='white', font=('Arial', 12)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cancel", command=settings_window.destroy,
                 bg='#e74c3c', fg='white', font=('Arial', 12)).pack(side=tk.LEFT, padx=5)
    
    def refresh_dashboard(self):
        """Refresh the dashboard display"""
        self.update_gui()
        self.update_data_summary()
        if self.is_connected:
            try:
                # Request fresh data from Arduino
                self.serial_connection.write("REQUEST_DATA\n".encode())
            except:
                pass
        self.add_activity("🔄 Dashboard refreshed")
    
    def save_historical_data(self):
        """Save historical data to file"""
        data = {
            'minute_data': dict(self.minute_data),
            'hourly_data': dict(self.hourly_data),
            'daily_data': dict(self.daily_data),
            'monthly_data': dict(self.monthly_data),
            'yearly_data': dict(self.yearly_data),
            'settings': {
                'dry_threshold': self.dry_threshold,
                'wet_threshold': self.wet_threshold,
                'flow_rate': self.flow_rate,
                'port': self.port
            },
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def load_historical_data(self):
        """Load historical data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load all data levels
                    self.minute_data = defaultdict(lambda: {
                        'water_used': 0.0, 'moisture': 0, 'events': 0, 'pump_duration': 0.0
                    })
                    self.minute_data.update(data.get('minute_data', {}))
                    
                    self.hourly_data = defaultdict(lambda: {
                        'water_used': 0.0, 'moisture': 0, 'events': 0, 'pump_duration': 0.0
                    })
                    self.hourly_data.update(data.get('hourly_data', {}))
                    
                    self.daily_data = defaultdict(lambda: {
                        'water_used': 0.0, 'moisture_avg': 0, 'events': 0, 'pump_duration': 0.0
                    })
                    self.daily_data.update(data.get('daily_data', {}))
                    
                    self.monthly_data = defaultdict(lambda: {
                        'water_used': 0.0, 'moisture_avg': 0, 'events': 0, 'pump_duration': 0.0
                    })
                    self.monthly_data.update(data.get('monthly_data', {}))
                    
                    self.yearly_data = defaultdict(lambda: {
                        'water_used': 0.0, 'moisture_avg': 0, 'events': 0, 'pump_duration': 0.0
                    })
                    self.yearly_data.update(data.get('yearly_data', {}))
                    
                    # Load settings
                    settings = data.get('settings', {})
                    self.dry_threshold = settings.get('dry_threshold', 400)
                    self.wet_threshold = settings.get('wet_threshold', 200)
                    self.flow_rate = settings.get('flow_rate', 1.0)
                    if 'port' in settings:
                        self.port = settings['port']
                        
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def run(self):
        """Start the monitoring system"""
        print("💧 Smart Irrigation Monitor Started")
        print(f"📡 Configured for port: {self.port}")
        print("🖥️ GUI Dashboard launching...")
        
        # Initialize data summary
        self.update_data_summary()
        
        def on_closing():
            if self.is_connected:
                self.disconnect_arduino()
            self.monitoring_active = False
            self.save_historical_data()
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            on_closing()

# Main execution
if __name__ == "__main__":
    # Configuration - Update COM port as needed
    ARDUINO_PORT = 'COM6'  # Change to your Arduino port
    BAUD_RATE = 9600
    
    print("🚀 Starting Smart Irrigation System...")
    print("=" * 50)
    
    try:
        monitor = SmartIrrigationMonitor(port=ARDUINO_PORT, baudrate=BAUD_RATE)
        monitor.run()
    except Exception as e:
        print(f"❌ Error starting system: {e}")
        input("Press Enter to exit...")
    
    print("👋 Smart Irrigation System stopped.")