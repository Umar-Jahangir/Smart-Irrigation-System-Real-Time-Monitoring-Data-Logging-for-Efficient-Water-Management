import serial
import time
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import tkinter as tk
from tkinter import ttk, messagebox

class SmartIrrigationMonitor:
    def __init__(self, port='COM6', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_connected = False
        self.total_water_used = 0.0
        
        # Irrigation data
        self.current_moisture = 0
        self.pump_status = False
        self.total_water_used_today = 0.0
        self.watering_events_today = 0
        
        # Thresholds
        self.dry_threshold = 400
        self.wet_threshold = 200
        self.flow_rate = 1.0  # liters per minute
        
        # Historical data storage
        self.daily_data = defaultdict(lambda: {'water_used': 0.0, 'events': 0})
        self.hourly_data = defaultdict(lambda: {'water_used': 0.0, 'moisture': 0})
        self.recent_activity = deque(maxlen=50)
        
        # Data file for persistence
        self.data_file = 'irrigation_data.json'
        self.load_historical_data()
        
        # GUI setup
        self.setup_gui()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_arduino, daemon=True)
        self.monitoring_active = True
        
    def setup_gui(self):
        """Create the irrigation dashboard"""
        self.root = tk.Tk()
        self.root.title("Smart Irrigation System Dashboard")
        self.root.geometry("800x600")
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
        
        # Connect button
        self.connect_btn = tk.Button(conn_frame, text="Connect", 
                                    command=self.toggle_connection,
                                    bg='#3498db', fg='white', 
                                    font=('Arial', 10))
        self.connect_btn.pack(side=tk.LEFT, padx=10)
        
        # Current Status Section
        status_frame = tk.LabelFrame(self.root, text="Current Status", 
                                   font=('Arial', 14, 'bold'),
                                   fg='white', bg='#34495e')
        status_frame.pack(pady=10, padx=20, fill='x')
        
        # Moisture level display
        self.moisture_label = tk.Label(status_frame, 
                                     text=f"Soil Moisture: {self.current_moisture}",
                                     font=('Arial', 14),
                                     fg='white', bg='#34495e')
        self.moisture_label.pack(pady=5)
        
        # Moisture status indicator
        self.moisture_status = tk.Label(status_frame, 
                                       text="Status: UNKNOWN",
                                       font=('Arial', 12, 'bold'),
                                       bg='#34495e')
        self.moisture_status.pack(pady=5)
        
        # Pump status
        self.pump_label = tk.Label(status_frame, 
                                 text="Pump: INACTIVE",
                                 font=('Arial', 12),
                                 fg='white', bg='#34495e')
        self.pump_label.pack(pady=5)
        
        # Today's Statistics Section
        today_frame = tk.LabelFrame(self.root, text="Today's Statistics", 
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

        # Recent Activity Section
        activity_frame = tk.LabelFrame(self.root, text="Recent Activity", 
                                     font=('Arial', 14, 'bold'),
                                     fg='white', bg='#34495e')
        activity_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        # Activity listbox with scrollbar
        listbox_frame = tk.Frame(activity_frame, bg='#34495e')
        listbox_frame.pack(fill='both', expand=True, pady=10)
        
        self.activity_listbox = tk.Listbox(listbox_frame, 
                                         font=('Arial', 10),
                                         bg='#2c3e50', fg='white',
                                         selectbackground='#3498db')
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.activity_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        
        self.activity_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.activity_listbox.yview)
        
        # Control Buttons Section
        button_frame = tk.Frame(self.root, bg='#2c3e50')
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="📊 Show Daily Usage", 
                 command=self.show_daily_usage,
                 bg='#9b59b6', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="📈 Show Moisture History", 
                 command=self.show_moisture_history,
                 bg='#e67e22', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="💾 Export Data", 
                 command=self.export_data,
                 bg='#16a085', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="⚙️ Settings", 
                 command=self.show_settings,
                 bg='#3498db', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🔄 Refresh", 
                 command=self.refresh_dashboard,
                 bg='#2ecc71', fg='white', 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    def toggle_connection(self):
        """Toggle Arduino connection"""
        if not self.is_connected:
            self.connect_to_arduino()
        else:
            self.disconnect_arduino()
    
    def connect_to_arduino(self):
        """Establish connection with Arduino"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            self.is_connected = True
            self.conn_status_label.config(text="🟢 Connected", fg='green')
            self.connect_btn.config(text="Disconnect")
            
            if not self.monitoring_thread.is_alive():
                self.monitoring_thread = threading.Thread(target=self.monitor_arduino, daemon=True)
                self.monitoring_thread.start()
            
            self.add_activity("✅ Connected to Arduino")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
    
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
        if data.startswith("IRRIGATION_DATA:"):  # Make sure this matches exactly what Arduino sends
            try:
                data_part = data.replace("IRRIGATION_DATA:", "")
                params = {}
                for param in data_part.split(","):
                    key, value = param.split("=")
                    if key == "MOISTURE":
                        params[key] = int(value)
                    elif key == "PUMP":
                        params[key] = bool(int(value))
                    elif key in ["WATER_USED", "TOTAL"]:
                        params[key] = float(value)
                    elif key == "EVENTS":
                        params[key] = int(value)
                
                # These lines WERE incorrectly indented before!
                self.current_moisture = params.get("MOISTURE", 0)
                self.pump_status = params.get("PUMP", False)
                self.total_water_used_today = params.get("WATER_USED", 0.0)
                self.watering_events_today = params.get("EVENTS", 0)
                self.total_water_used = params.get("TOTAL", 0.0)
                
                self.update_historical_data()
                self.root.after(0, self.update_gui)
                
                self.add_activity(
                    f"Water: {params.get('WATER_USED', 0):.2f}L (Today: {self.total_water_used_today:.2f}L)"
                )
                
            except ValueError as e:
                print(f"Data parsing error: {e}")
                self.add_activity(f"[ERROR] Bad data: {data}")
        
    
    def update_historical_data(self):
        """Update historical data records"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%Y-%m-%d %H:00")
        
        # Update daily data
        self.daily_data[today]['water_used'] = self.total_water_used_today
        self.daily_data[today]['events'] = self.watering_events_today
        
        # Update hourly data
        self.hourly_data[current_hour]['water_used'] = self.total_water_used_today
        self.hourly_data[current_hour]['moisture'] = self.current_moisture
        
        # Auto-save data every 5 updates
        if self.watering_events_today % 5 == 0:
            self.save_historical_data()
    
    def update_gui(self):
        """Update GUI elements with current data"""
        # Update current status
        self.moisture_label.config(text=f"Soil Moisture: {self.current_moisture}")
        
        # Update moisture status with color coding
        if self.current_moisture > self.dry_threshold:
            status = "DRY"
            color = '#e74c3c'  # Red
        elif self.current_moisture < self.wet_threshold:
            status = "WET"
            color = '#27ae60'  # Green
        else:
            status = "OK"
            color = '#f39c12'  # Orange
            
        self.moisture_status.config(text=f"Status: {status}", fg=color)
        self.total_label.config(text=f"Lifetime Total: {self.total_water_used:.2f} L")
        
        # Update pump status
        self.pump_label.config(text=f"Pump: {'ACTIVE' if self.pump_status else 'INACTIVE'}",
                             fg='#3498db' if self.pump_status else '#95a5a6')
        
        # Update today's statistics
        self.water_used_label.config(text=f"Water Used: {self.total_water_used_today:.2f} L")
        self.events_label.config(text=f"Watering Events: {self.watering_events_today}")
    
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
    
    def show_daily_usage(self):
        """Show daily water usage graph"""
        if not self.daily_data:
            messagebox.showinfo("No Data", "No daily data available to display")
            return
        
        dates = sorted(self.daily_data.keys())
        water_used = [self.daily_data[date]['water_used'] for date in dates]
        events = [self.daily_data[date]['events'] for date in dates]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Water usage graph
        ax1.bar(dates, water_used, color='#3498db', alpha=0.7)
        ax1.set_title('Daily Water Usage', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Liters')
        ax1.grid(True, alpha=0.3)
        
        # Watering events graph
        ax2.bar(dates, events, color='#2ecc71', alpha=0.7)
        ax2.set_title('Daily Watering Events', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Events')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def show_moisture_history(self):
        """Show hourly moisture history for today"""
        today = datetime.now().strftime("%Y-%m-%d")
        hourly_today = {k: v for k, v in self.hourly_data.items() if k.startswith(today)}
        
        if not hourly_today:
            messagebox.showinfo("No Data", "No hourly data available for today")
            return
        
        hours = sorted(hourly_today.keys())
        moisture = [hourly_today[hour]['moisture'] for hour in hours]
        hour_labels = [datetime.strptime(h, "%Y-%m-%d %H:%M").strftime("%H:%M") for h in hours]
        
        plt.figure(figsize=(12, 6))
        
        # Plot moisture levels
        plt.plot(hour_labels, moisture, marker='o', color='#9b59b6', 
                label='Moisture Level', linewidth=2)
        
        # Add threshold lines
        plt.axhline(y=self.dry_threshold, color='red', linestyle='--', 
                   label=f'Dry Threshold ({self.dry_threshold})')
        plt.axhline(y=self.wet_threshold, color='green', linestyle='--', 
                   label=f'Wet Threshold ({self.wet_threshold})')
        
        plt.title(f'Soil Moisture History - {today}', fontsize=14, fontweight='bold')
        plt.xlabel('Time (Hour)')
        plt.ylabel('Moisture Level')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def export_data(self):
        """Export data to JSON file"""
        data = {
            'daily_data': dict(self.daily_data),
            'hourly_data': dict(self.hourly_data),
            'thresholds': {
                'dry': self.dry_threshold,
                'wet': self.wet_threshold,
                'flow_rate': self.flow_rate
            },
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open('irrigation_export.json', 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export Successful", "Data exported to irrigation_export.json")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def show_settings(self):
        """Show settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("System Settings")
        settings_window.geometry("400x300")
        
        # Dry threshold setting
        tk.Label(settings_window, text="Dry Threshold:").pack(pady=5)
        dry_spin = tk.Spinbox(settings_window, from_=0, to=1023, 
                             font=('Arial', 12), width=10)
        dry_spin.pack()
        dry_spin.delete(0, tk.END)
        dry_spin.insert(0, str(self.dry_threshold))
        
        # Wet threshold setting
        tk.Label(settings_window, text="Wet Threshold:").pack(pady=5)
        wet_spin = tk.Spinbox(settings_window, from_=0, to=1023, 
                            font=('Arial', 12), width=10)
        wet_spin.pack()
        wet_spin.delete(0, tk.END)
        wet_spin.insert(0, str(self.wet_threshold))
        
        # Flow rate setting
        tk.Label(settings_window, text="Flow Rate (L/min):").pack(pady=5)
        flow_spin = tk.Spinbox(settings_window, from_=0.1, to=10.0, increment=0.1,
                             font=('Arial', 12), width=10)
        flow_spin.pack()
        flow_spin.delete(0, tk.END)
        flow_spin.insert(0, f"{self.flow_rate:.1f}")
        
        def save_settings():
            try:
                self.dry_threshold = int(dry_spin.get())
                self.wet_threshold = int(wet_spin.get())
                self.flow_rate = float(flow_spin.get())
                
                if self.is_connected:
                    # Send new settings to Arduino
                    settings_cmd = f"SETTINGS:DRY={self.dry_threshold},WET={self.wet_threshold},FLOW={self.flow_rate}\n"
                    self.serial_connection.write(settings_cmd.encode())
                
                messagebox.showinfo("Success", "Settings updated successfully!")
                settings_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid settings: {str(e)}")
        
        tk.Button(settings_window, text="Save", command=save_settings,
                 bg='#2ecc71', fg='white', font=('Arial', 12)).pack(pady=20)
    
    def refresh_dashboard(self):
        """Refresh the dashboard display"""
        self.update_gui()
        if self.is_connected:
            # Request fresh data from Arduino
            self.serial_connection.write("REQUEST_DATA\n".encode())
    
    def save_historical_data(self):
        """Save historical data to file"""
        data = {
            'daily_data': dict(self.daily_data),
            'hourly_data': dict(self.hourly_data),
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def load_historical_data(self):
        """Load historical data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.daily_data = defaultdict(lambda: {'water_used': 0.0, 'events': 0})
                    self.daily_data.update(data.get('daily_data', {}))
                    self.hourly_data = defaultdict(lambda: {'water_used': 0.0, 'moisture': 0})
                    self.hourly_data.update(data.get('hourly_data', {}))
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def run(self):
        """Start the monitoring system"""
        print("💧 Smart Irrigation Monitor Started")
        print(f"📡 Configured for port: {self.port}")
        print("🖥️  GUI Dashboard launching...")
        
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