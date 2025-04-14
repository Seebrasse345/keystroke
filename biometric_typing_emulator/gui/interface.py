import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import json
import time
from threading import Thread

# Add parent directory to sys.path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from other modules
from recorder.record_typing import TypingRecorder
from generator.generate_sequence import TypingSequenceGenerator

class BiometricTypingEmulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Biometric Typing Emulator")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"), background="#f0f0f0")
        self.style.configure("SubHeader.TLabel", font=("Arial", 12), background="#f0f0f0")
        
        # Create tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tab frames
        self.main_tab = ttk.Frame(self.notebook)
        self.record_tab = ttk.Frame(self.notebook)
        self.profile_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.main_tab, text="Generate & Replay")
        self.notebook.add(self.record_tab, text="Record")
        self.notebook.add(self.profile_tab, text="Profile Analysis")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Initialize tabs
        self.init_main_tab()
        self.init_record_tab()
        self.init_profile_tab()
        self.init_settings_tab()
        
        # Load settings
        self.load_settings()

    def init_main_tab(self):
        """Initialize the main tab with generation and replay controls"""
        frame = ttk.Frame(self.main_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add header
        header = ttk.Label(frame, text="Generate & Replay Typing Sequence", style="Header.TLabel")
        header.pack(pady=(0, 10), anchor=tk.W)
        
        # User profile selection
        user_frame = ttk.Frame(frame)
        user_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(user_frame, text="Profile:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.users = self.get_available_users()
        self.user_var = tk.StringVar(value=self.users[0] if self.users else "")
        self.user_combo = ttk.Combobox(user_frame, textvariable=self.user_var, values=self.users, state="readonly", width=15)
        self.user_combo.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(user_frame, text="Refresh", command=self.refresh_users)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Text input
        ttk.Label(frame, text="Text to Type:", style="SubHeader.TLabel").pack(pady=(15, 5), anchor=tk.W)
        
        self.text_input = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=8)
        self.text_input.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Options for generation
        options_frame = ttk.LabelFrame(frame, text="Generation Options")
        options_frame.pack(fill=tk.X, pady=10)
        
        options_grid = ttk.Frame(options_frame)
        options_grid.pack(fill=tk.X, padx=10, pady=5)
        
        # Add random corrections checkbox (adjust grid position)
        self.add_corrections_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_grid, text="Add occasional corrections (typos)", variable=self.add_corrections_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5) # Span both columns now
        
        # Button frame
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=15)
        
        # Create a themed button style
        self.style.configure("Generate.TButton", font=("Arial", 10, "bold"))
        
        # Generate button
        self.generate_btn = ttk.Button(
            btn_frame, 
            text="Generate Sequence", 
            style="Generate.TButton",
            command=self.generate_sequence
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        # Generate & Replay button
        self.replay_btn = ttk.Button(
            btn_frame, 
            text="Generate & Replay", 
            style="Generate.TButton",
            command=self.generate_and_replay
        )
        self.replay_btn.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

    def init_record_tab(self):
        """Initialize the recording tab"""
        frame = ttk.Frame(self.record_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add header
        header = ttk.Label(frame, text="Record Typing Biometrics", style="Header.TLabel")
        header.pack(pady=(0, 10), anchor=tk.W)
        
        # User selection
        user_frame = ttk.Frame(frame)
        user_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(user_frame, text="Save as Profile:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Use the same user list from main tab
        user_combo = ttk.Combobox(user_frame, textvariable=self.user_var, values=self.users, width=15)
        user_combo.pack(side=tk.LEFT, padx=5)
        
        # Create new user
        ttk.Label(user_frame, text="New Profile:").pack(side=tk.LEFT, padx=(15, 5))
        
        self.new_user_var = tk.StringVar()
        new_user_entry = ttk.Entry(user_frame, textvariable=self.new_user_var, width=15)
        new_user_entry.pack(side=tk.LEFT, padx=5)
        
        create_user_btn = ttk.Button(user_frame, text="Create", command=self.create_user)
        create_user_btn.pack(side=tk.LEFT, padx=5)
        
        # Text area for typing
        ttk.Label(frame, text="Type or Paste Text Here:", style="SubHeader.TLabel").pack(pady=(15, 5), anchor=tk.W)
        
        self.record_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=8)
        self.record_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Instructions
        instructions = ttk.Label(frame, text="Type naturally with your usual speed and rhythm. The system records key press timings, delays, etc.")
        instructions.pack(pady=5, anchor=tk.W)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=15)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Recording", command=self.start_recording)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Recording", command=self.stop_recording, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.record_status_var = tk.StringVar(value="Ready")
        record_status = ttk.Label(frame, textvariable=self.record_status_var, relief=tk.SUNKEN, anchor=tk.W)
        record_status.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        # Recorder instance
        self.recorder = None

    def init_profile_tab(self):
        """Initialize the profile analysis tab"""
        frame = ttk.Frame(self.profile_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add header
        header = ttk.Label(frame, text="Profile Analysis", style="Header.TLabel")
        header.pack(pady=(0, 10), anchor=tk.W)
        
        # User selection
        profile_frame = ttk.Frame(frame)
        profile_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(profile_frame, text="Select Profile:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Use a separate profile variable for analysis
        self.profile_var = tk.StringVar(value=self.users[0] if self.users else "")
        profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, values=self.users, state="readonly", width=15)
        profile_combo.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(profile_frame, text="Refresh", command=self.refresh_users)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        load_btn = ttk.Button(profile_frame, text="Load Profile", command=self.load_profile_data)
        load_btn.pack(side=tk.LEFT, padx=5)
        
        # Profile information
        profile_info_frame = ttk.LabelFrame(frame, text="Profile Information")
        profile_info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Profile data display (scrolled text)
        self.profile_text = scrolledtext.ScrolledText(profile_info_frame, wrap=tk.WORD, height=8)
        self.profile_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Profile actions
        actions_frame = ttk.Frame(frame)
        actions_frame.pack(fill=tk.X, pady=5)
        
        export_btn = ttk.Button(actions_frame, text="Export Profile", command=self.export_profile)
        export_btn.pack(side=tk.LEFT, padx=5)
        
        import_btn = ttk.Button(actions_frame, text="Import Profile", command=self.import_profile)
        import_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = ttk.Button(actions_frame, text="Delete Profile", command=self.delete_profile)
        delete_btn.pack(side=tk.LEFT, padx=5)

    def init_settings_tab(self):
        """Initialize the settings tab"""
        frame = ttk.Frame(self.settings_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add header
        header = ttk.Label(frame, text="Settings", style="Header.TLabel")
        header.pack(pady=(0, 10), anchor=tk.W)
        
        # AHK path setting
        ahk_frame = ttk.Frame(frame)
        ahk_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(ahk_frame, text="AutoHotkey Path:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.ahk_path_var = tk.StringVar()
        ahk_entry = ttk.Entry(ahk_frame, textvariable=self.ahk_path_var, width=40)
        ahk_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(ahk_frame, text="Browse", command=self.browse_ahk)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Default options
        options_frame = ttk.LabelFrame(frame, text="Default Options")
        options_frame.pack(fill=tk.X, pady=10)
        
        # Default user
        user_frame = ttk.Frame(options_frame)
        user_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(user_frame, text="Default Profile:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.default_user_var = tk.StringVar()
        default_user_combo = ttk.Combobox(user_frame, textvariable=self.default_user_var, values=self.users, width=15)
        default_user_combo.pack(side=tk.LEFT, padx=5)
        
        # Save settings button
        save_btn = ttk.Button(frame, text="Save Settings", command=self.save_settings)
        save_btn.pack(pady=10)
        
        # Check AHK installation
        check_frame = ttk.Frame(frame)
        check_frame.pack(fill=tk.X, pady=10)
        
        check_ahk_btn = ttk.Button(check_frame, text="Check AHK Installation", command=self.check_ahk)
        check_ahk_btn.pack(side=tk.LEFT, padx=5)
        
        self.ahk_status_var = tk.StringVar(value="Unknown")
        ahk_status = ttk.Label(check_frame, textvariable=self.ahk_status_var)
        ahk_status.pack(side=tk.LEFT, padx=10)

    def get_available_users(self):
        """Get list of available user profiles"""
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
        return [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
    
    def refresh_users(self):
        """Refresh the user profiles list"""
        self.users = self.get_available_users()
        self.user_combo["values"] = self.users
        if self.users and not self.user_var.get() in self.users:
            self.user_var.set(self.users[0])
            
    def create_user(self):
        """Create a new user profile"""
        new_user = self.new_user_var.get().strip()
        if not new_user:
            messagebox.showerror("Error", "Please enter a username")
            return
            
        # Check if user already exists
        if new_user in self.users:
            messagebox.showerror("Error", f"User '{new_user}' already exists")
            return
            
        # Create user directory
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
        user_dir = os.path.join(profiles_dir, new_user)
        os.makedirs(user_dir, exist_ok=True)
        
        # Update users list
        self.refresh_users()
        self.user_var.set(new_user)
        messagebox.showinfo("Success", f"User profile '{new_user}' created")
        
        # Clear entry
        self.new_user_var.set("")
    
    def start_recording(self):
        """Start recording typing biometrics"""
        user_id = self.user_var.get()
        if not user_id:
            messagebox.showerror("Error", "Please select or create a user profile")
            return
            
        self.recorder = TypingRecorder(user_id)
        self.recorder.start_recording()
        
        # Update UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.record_status_var.set(f"Recording typing for user '{user_id}'...")
    
    def stop_recording(self):
        """Stop recording typing biometrics"""
        if self.recorder:
            self.recorder.stop_recording()
            
        # Update UI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.record_status_var.set("Recording stopped. Profile updated.")
        
        # Refresh user profiles list
        self.refresh_users()
    
    def generate_sequence(self):
        """Generate typing sequence from profile data"""
        user_id = self.user_var.get()
        if not user_id:
            messagebox.showerror("Error", "Please select a user profile")
            return
            
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("Error", "Please enter text to generate")
            return
            
        try:
            self.status_var.set("Generating typing sequence...")
            self.generate_btn.config(state=tk.DISABLED)
            self.replay_btn.config(state=tk.DISABLED)
            self.root.update()
            
            # Generate the sequence
            generator = TypingSequenceGenerator(user_id)
            sequence = generator.generate_sequence(
                text,
                add_corrections=self.add_corrections_var.get()
            )
            output_path = generator.save_sequence(sequence)
            
            self.status_var.set(f"Sequence generated successfully: {output_path}")
            messagebox.showinfo("Success", f"Typing sequence generated successfully.\nSaved to: {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate sequence: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
        finally:
            self.generate_btn.config(state=tk.NORMAL)
            self.replay_btn.config(state=tk.NORMAL)
    
    def generate_and_replay(self):
        """Generate typing sequence and replay it with AHK"""
        user_id = self.user_var.get()
        if not user_id:
            messagebox.showerror("Error", "Please select a user profile")
            return
            
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("Error", "Please enter text to generate")
            return
            
        # Check if AHK is configured
        if not self.check_ahk_path():
            messagebox.showerror("Error", "AutoHotkey not configured. Please set the path in Settings.")
            return
            
        try:
            self.status_var.set("Generating typing sequence...")
            self.generate_btn.config(state=tk.DISABLED)
            self.replay_btn.config(state=tk.DISABLED)
            self.root.update()
            
            # Generate the sequence
            generator = TypingSequenceGenerator(user_id)
            sequence = generator.generate_sequence(
                text,
                add_corrections=self.add_corrections_var.get()
            )
            output_path = generator.save_sequence(sequence)
            
            self.status_var.set(f"Sequence generated. Launching AHK replay...")
            
            # Launch AHK script in a separate thread
            thread = Thread(target=self.run_ahk_script, args=(output_path,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate sequence: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            self.generate_btn.config(state=tk.NORMAL)
            self.replay_btn.config(state=tk.NORMAL)
    
    def run_ahk_script(self, sequence_path):
        """Run the AHK script to replay typing"""
        try:
            # Get AHK path from settings
            ahk_path = self.ahk_path_var.get()
            
            # Get script path
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "replay_tool",
                "inject_typing.ahk"
            )
            
            # Run the AHK script
            subprocess.run([ahk_path, script_path, sequence_path], check=True)
            
            # Update UI when done
            self.root.after(0, lambda: self.status_var.set("Replay completed successfully."))
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.replay_btn.config(state=tk.NORMAL))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to run AHK script: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.replay_btn.config(state=tk.NORMAL))
    
    def load_profile_data(self):
        """Load and display selected profile data"""
        profile_id = self.profile_var.get()
        if not profile_id:
            messagebox.showerror("Error", "Please select a profile")
            return
            
        try:
            # Load profile data
            profile_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "profiles",
                profile_id,
                f"{profile_id}_profile.json"
            )
            
            if not os.path.exists(profile_path):
                messagebox.showerror("Error", f"Profile file not found: {profile_path}")
                return
                
            with open(profile_path, 'r') as f:
                profile_data = json.load(f)
                
            # Format and display profile data
            self.profile_text.delete("1.0", tk.END)
            
            # Add profile info
            self.profile_text.insert(tk.END, f"Profile: {profile_id}\n")
            self.profile_text.insert(tk.END, f"Session Count: {profile_data.get('session_count', 0)}\n\n")
            
            # Add dwell time stats
            self.profile_text.insert(tk.END, "=== Dwell Times (ms) ===\n")
            dwell_times = profile_data.get('mean_dwell_times', {})
            for key, value in sorted(dwell_times.items()):
                std = profile_data.get('std_dwell_times', {}).get(key, 0)
                self.profile_text.insert(tk.END, f"{key}: {value:.2f} ± {std:.2f}\n")
            
            # Add flight time stats
            self.profile_text.insert(tk.END, "\n=== Flight Times (ms) ===\n")
            flight_times = profile_data.get('mean_flight_times', {})
            for key_pair, value in sorted(flight_times.items()):
                std = profile_data.get('std_flight_times', {}).get(key_pair, 0)
                self.profile_text.insert(tk.END, f"{key_pair}: {value:.2f} ± {std:.2f}\n")
                
            # Add typo pattern information if available
            if 'typo_rate' in profile_data:
                self.profile_text.insert(tk.END, "\n=== Typo Patterns ===\n")
                self.profile_text.insert(tk.END, f"Overall Typo Rate: {profile_data['typo_rate']:.4f}\n\n")
                
                # Add error type distribution
                self.profile_text.insert(tk.END, "Error Type Distribution:\n")
                for error_type in ['double_letter_error_rate', 'inserted_letter_rate', 'missed_letter_rate', 'reversed_letters_rate']:
                    if error_type in profile_data:
                        # Format the error type name nicely
                        name = error_type.replace('_rate', '').replace('_', ' ').title()
                        self.profile_text.insert(tk.END, f"- {name}: {profile_data[error_type]:.4f}\n")
                
                # Add correction style
                if 'correction_style' in profile_data:
                    style = profile_data['correction_style']
                    total = style.get('immediate', 0) + style.get('delayed', 0)
                    if total > 0:
                        immediate_pct = (style.get('immediate', 0) / total) * 100
                        delayed_pct = (style.get('delayed', 0) / total) * 100
                        self.profile_text.insert(tk.END, f"\nCorrection Style:\n")
                        self.profile_text.insert(tk.END, f"- Immediate: {immediate_pct:.1f}%\n")
                        self.profile_text.insert(tk.END, f"- Delayed: {delayed_pct:.1f}%\n")
                
                # Add error clustering information
                if 'typo_clusters' in profile_data:
                    clusters = profile_data['typo_clusters']
                    total = (clusters.get('home_row', 0) + clusters.get('adjacent_keys', 0) + 
                             clusters.get('same_hand', 0) + clusters.get('other', 0))
                    
                    if total > 0:
                        self.profile_text.insert(tk.END, f"\nTypo Clusters:\n")
                        for cluster, value in clusters.items():
                            cluster_name = cluster.replace('_', ' ').title()
                            cluster_pct = (value / total) * 100
                            self.profile_text.insert(tk.END, f"- {cluster_name}: {cluster_pct:.1f}%\n")
                
                # Add common typo patterns
                if 'common_typo_patterns' in profile_data:
                    patterns = profile_data['common_typo_patterns']
                    if patterns:
                        self.profile_text.insert(tk.END, f"\nCommon Typo Patterns (Top 10):\n")
                        for i, (pattern, freq) in enumerate(list(patterns.items())[:10]):
                            self.profile_text.insert(tk.END, f"{i+1}. '{pattern}' : {freq:.2f}\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}")
    
    def export_profile(self):
        """Export the selected profile to a file"""
        profile_id = self.profile_var.get()
        if not profile_id:
            messagebox.showerror("Error", "Please select a profile")
            return
            
        try:
            # Get profile path
            profile_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "profiles",
                profile_id,
                f"{profile_id}_profile.json"
            )
            
            if not os.path.exists(profile_path):
                messagebox.showerror("Error", f"Profile file not found: {profile_path}")
                return
                
            # Ask for export location
            export_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=f"{profile_id}_profile.json"
            )
            
            if not export_path:
                return  # User canceled
                
            # Copy the file
            with open(profile_path, 'r') as src, open(export_path, 'w') as dst:
                dst.write(src.read())
                
            messagebox.showinfo("Success", f"Profile exported to {export_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export profile: {str(e)}")
    
    def import_profile(self):
        """Import a profile from a file"""
        try:
            # Ask for import file
            import_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Select profile file to import"
            )
            
            if not import_path:
                return  # User canceled
                
            # Load the file to validate it
            with open(import_path, 'r') as f:
                profile_data = json.load(f)
                
            # Check if it's a valid profile
            if not all(k in profile_data for k in ['mean_dwell_times', 'mean_flight_times', 'session_count']):
                messagebox.showerror("Error", "The selected file is not a valid profile")
                return
                
            # Ask for profile name
            profile_name = self.new_user_var.get().strip()
            if not profile_name:
                messagebox.showerror("Error", "Please enter a profile name in the 'New Profile' field")
                return
                
            # Create profile directory
            profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
            profile_dir = os.path.join(profiles_dir, profile_name)
            os.makedirs(profile_dir, exist_ok=True)
            
            # Save the profile
            profile_path = os.path.join(profile_dir, f"{profile_name}_profile.json")
            with open(import_path, 'r') as src, open(profile_path, 'w') as dst:
                dst.write(src.read())
                
            # Refresh the user list
            self.refresh_users()
            
            messagebox.showinfo("Success", f"Profile imported as {profile_name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import profile: {str(e)}")
    
    def delete_profile(self):
        """Delete the selected profile"""
        profile_id = self.profile_var.get()
        if not profile_id:
            messagebox.showerror("Error", "Please select a profile")
            return
            
        # Confirm deletion
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete the profile '{profile_id}'?"):
            return
            
        try:
            # Get profile directory
            profile_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "profiles",
                profile_id
            )
            
            if not os.path.exists(profile_dir):
                messagebox.showerror("Error", f"Profile directory not found: {profile_dir}")
                return
                
            # Delete the directory and its contents
            import shutil
            shutil.rmtree(profile_dir)
            
            # Refresh the user list
            self.refresh_users()
            
            messagebox.showinfo("Success", f"Profile '{profile_id}' deleted")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")
    
    def check_ahk_path(self):
        """Check if the AHK path is valid"""
        ahk_path = self.ahk_path_var.get()
        return os.path.exists(ahk_path) and ahk_path.lower().endswith('.exe')
    
    def browse_ahk(self):
        """Browse for AHK executable"""
        ahk_path = filedialog.askopenfilename(
            filetypes=[("Executable", "*.exe")],
            title="Select AutoHotkey executable"
        )
        
        if ahk_path:
            self.ahk_path_var.set(ahk_path)
    
    def check_ahk(self):
        """Check if AHK is installed and configured correctly"""
        ahk_path = self.ahk_path_var.get()
        
        if not ahk_path:
            self.ahk_status_var.set("Not configured")
            return
            
        if not os.path.exists(ahk_path):
            self.ahk_status_var.set("File not found")
            return
            
        try:
            # Run AHK with version parameter
            result = subprocess.run([ahk_path, "/version"], capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                version = result.stdout.strip() if result.stdout else "Unknown version"
                self.ahk_status_var.set(f"Installed: {version}")
            else:
                self.ahk_status_var.set("Error running AHK")
                
        except Exception as e:
            self.ahk_status_var.set(f"Error: {str(e)}")
    
    def load_settings(self):
        """Load application settings"""
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "settings.json"
        )
        
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    
                # Apply settings
                if 'ahk_path' in settings:
                    self.ahk_path_var.set(settings['ahk_path'])
                    
                if 'default_user' in settings and settings['default_user'] in self.users:
                    self.default_user_var.set(settings['default_user'])
                    self.user_var.set(settings['default_user'])
                    
            except Exception as e:
                print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save application settings"""
        settings = {
            'ahk_path': self.ahk_path_var.get(),
            'default_user': self.default_user_var.get()
        }
        
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "settings.json"
        )
        
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
                
            messagebox.showinfo("Success", "Settings saved successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")


def main():
    root = tk.Tk()
    app = BiometricTypingEmulatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 