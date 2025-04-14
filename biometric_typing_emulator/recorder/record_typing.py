import time
import json
import os
import csv
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import keyboard
import statistics
import numpy as np

class TypingRecorder:
    def __init__(self, user_id):
        self.user_id = user_id
        self.recording = False
        self.keys = []
        self.keydown_times = {}
        self.last_keyup_time = None
        self.session_data = []
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"session_{user_id}_{self.timestamp}"
        
        # For typo pattern tracking
        self.typed_text = ""
        self.correction_positions = []
        self.typo_patterns = []
        self.last_keys = []  # Track sequence of recent keys for pattern detection
        self.max_pattern_length = 5  # Max length of tracked characters for pattern
        
        # Ensure profile directory exists
        self.profile_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profiles", user_id)
        if not os.path.exists(self.profile_dir):
            os.makedirs(self.profile_dir)
            
        self.profile_file = os.path.join(self.profile_dir, f"{user_id}_profile.json")
        self.initialize_profile()
    
        self.listener = None
    
    def initialize_profile(self):
        """Initialize or load existing user profile"""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r') as f:
                    self.profile = json.load(f)
            except Exception as e:
                print(f"Error loading profile: {e}")
                self.create_new_profile()
        else:
            self.create_new_profile()
    
    def create_new_profile(self):
        """Create a new profile if one doesn't exist"""
        self.profile = {
            "mean_dwell_times": {},
            "std_dwell_times": {},
            "mean_flight_times": {},
            "std_flight_times": {},
            "session_count": 0,
            # New typo pattern tracking fields
            "typo_rate": 0.0,
            "common_typo_patterns": {},
            "correction_style": {
                "immediate": 0,
                "delayed": 0
            },
            "typo_clusters": {
                "home_row": 0,
                "adjacent_keys": 0,
                "same_hand": 0,
                "other": 0
            },
            "double_letter_error_rate": 0.0,
            "inserted_letter_rate": 0.0,
            "missed_letter_rate": 0.0,
            "reversed_letters_rate": 0.0
        }
    
    def _key_to_string(self, key):
        if isinstance(key, keyboard.KeyCode):
            return key.char
        elif isinstance(key, keyboard.Key):
            # Map special keys to the strings used by the generator
            key_map = {
                keyboard.Key.space: "space",
                keyboard.Key.enter: "enter",
                keyboard.Key.backspace: "backspace",
                keyboard.Key.tab: "tab",
                # Add other mappings if needed (Shift, Ctrl, Alt, etc.)
                keyboard.Key.shift: "shift",
                keyboard.Key.ctrl: "ctrl", 
                keyboard.Key.alt: "alt",
                keyboard.Key.esc: "esc",
                # ... other special keys ...
            }
            return key_map.get(key, key.name) # Use key.name as fallback
        return None # Should not happen

    def start_recording(self):
        """Start recording keyboard events"""
        self.recording = True
        self.keys = []
        self.keydown_times = {}
        self.last_keyup_time = None
        self.session_data = []
        self.typed_text = ""
        self.correction_positions = []
        self.typo_patterns = []
        self.last_keys = []
        
        # Stop existing listener if any
        if self.listener and self.listener.is_alive():
            self.listener.stop()
            print("DEBUG: Stopped previous listener.")

        # Use pynput Listener
        try:
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            print("DEBUG: pynput listener started.")
            print(f"Recording started for user {self.user_id}")
        except Exception as e:
            print(f"ERROR: Failed to start pynput listener: {e}")
            self.recording = False # Ensure recording state is correct
            messagebox.showerror("Listener Error", f"Could not start keyboard listener. Ensure permissions are correct.\nError: {e}")
            # Optionally, re-raise or handle differently
    
    def stop_recording(self):
        """Stop recording and save the data"""
        print(f"DEBUG: stop_recording called. Current session_data length: {len(self.session_data)}")
        if not self.recording:
            return
            
        self.recording = False
        
        # Stop pynput listener
        if self.listener:
            self.listener.stop()
            print("DEBUG: pynput listener stopped.")
            self.listener = None # Clear the listener instance
        
        # Save the session data
        if self.session_data:
            self.save_session_data()
            self.analyze_typo_patterns()
            self.update_profile()
            print(f"Recording stopped. Saved session data and updated profile for {self.user_id}")
        else:
            print("No keystrokes recorded.")
    
    def _on_press(self, key):
        """Handle key press events from pynput listener."""
        if not self.recording:
            return
            
        key_str = self._key_to_string(key)
        if key_str is None:
            print(f"DEBUG: Ignoring unknown press event: {key}")
            return
        
        print(f"DEBUG: Press event: {key_str}")
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Avoid recording keydown time if already pressed (key repeat)
        if key_str not in self.keydown_times:
             self.keydown_times[key_str] = current_time
             print(f"DEBUG: Keydown time for {key_str} recorded: {current_time}")
        else:
             print(f"DEBUG: Keydown for {key_str} already recorded (repeat?), ignoring.")

    def _on_release(self, key):
        """Handle key release events from pynput listener."""
        if not self.recording:
            return

        key_str = self._key_to_string(key)
        if key_str is None:
            print(f"DEBUG: Ignoring unknown release event: {key}")
            return

        print(f"DEBUG: Release event: {key_str}")
        current_time = time.time() * 1000  # Convert to milliseconds
        
        if key_str in self.keydown_times:
            keydown_time = self.keydown_times[key_str]
            keyup_time = current_time
            dwell_time = keyup_time - keydown_time
            print(f"DEBUG: Dwell time for {key_str}: {dwell_time}")

            flight_time = 0
            if self.last_keyup_time is not None:
                flight_time = max(0, keydown_time - self.last_keyup_time) # Enforce non-negative
                print(f"DEBUG: Flight time before {key_str}: {flight_time}")
            
            is_correction = 0
            if key_str == 'backspace':
                is_correction = 1
                self.correction_positions.append(len(self.typed_text))
                if self.typed_text:
                    self.typed_text = self.typed_text[:-1]
                
                recent_keys = self.last_keys[-self.max_pattern_length:] if len(self.last_keys) > 0 else []
                if recent_keys:
                    self.typo_patterns.append({
                        "pattern": "".join(recent_keys),
                        "position": len(self.typed_text),
                        "timestamp": current_time
                    })
            else:
                # Only add printable single characters or known special keys like space to typed_text
                if len(key_str) == 1 or key_str == "space": 
                    # Add key_str to typed_text for analysis
                    # Note: You might want to map 'space' back to ' ' for text analysis
                    effective_char = key_str if key_str != "space" else " " 
                    self.typed_text += effective_char
                    
                    # Keep track of last *string* keys for pattern detection
                    self.last_keys.append(key_str) 
                    if len(self.last_keys) > self.max_pattern_length:
                        self.last_keys.pop(0)
            
            key_data = {
                "key": key_str, # Save the mapped string
                "keydown_time": keydown_time,
                "keyup_time": keyup_time,
                "dwell_time": dwell_time,
                "flight_time": flight_time,
                "is_correction": is_correction,
            }
            
            print(f"DEBUG: Prepared key_data: {key_data}")
            self.session_data.append(key_data)
            print(f"DEBUG: Appended key_data. session_data length: {len(self.session_data)}")
            self.keys.append(key_str)
            self.last_keyup_time = keyup_time
            
            del self.keydown_times[key_str]
        else:
             print(f"DEBUG: KeyUP event for {key_str} ignored, keydown_time not found.")
    
    def analyze_typo_patterns(self):
        """Analyze recorded typing data to extract typo patterns"""
        if not self.session_data:
            return
            
        # Calculate basic statistics
        total_keystrokes = len(self.session_data)
        correction_keystrokes = sum(1 for data in self.session_data if data.get("is_correction") == 1)
        
        # Calculate typo rate (percentage of keystrokes that are corrections)
        if total_keystrokes > 0:
            typo_rate = correction_keystrokes / total_keystrokes
        else:
            typo_rate = 0
            
        # Analyze immediate vs delayed corrections
        immediate_corrections = 0
        delayed_corrections = 0
        
        for i, pos in enumerate(self.correction_positions):
            if i > 0 and self.correction_positions[i] - self.correction_positions[i-1] <= 1:
                immediate_corrections += 1
            else:
                delayed_corrections += 1
                
        # Identify common typo patterns
        common_patterns = {}
        
        for pattern in self.typo_patterns:
            p = pattern["pattern"]
            if len(p) >= 2:  # Need at least 2 characters for meaningful pattern
                if p in common_patterns:
                    common_patterns[p] += 1
                else:
                    common_patterns[p] = 1
                    
        # Sort patterns by frequency
        sorted_patterns = {k: v for k, v in sorted(common_patterns.items(), 
                                                  key=lambda item: item[1], 
                                                  reverse=True)}
        
        # Categorize typo types using sequential analysis
        double_letter_errors = 0
        inserted_letter_errors = 0
        missed_letter_errors = 0
        reversed_letters_errors = 0
        
        # We'll do a simplified analysis here - a more complex analysis would parse
        # the full typing sequence and backspaces to identify exact error types
        for pattern in self.typo_patterns:
            p = pattern["pattern"]
            if len(p) >= 2:
                if p[-1] == p[-2]:  # Two same letters in a row
                    double_letter_errors += 1
                elif len(p) >= 3 and p[-3] == p[-1]:  # Possible reversal
                    reversed_letters_errors += 1
                else:
                    # Simplified categorization - would need more context for accuracy
                    inserted_letter_errors += 1
                    
        # Categorize by key location (simplified version)
        home_row_keys = "asdfghjkl;"
        home_row_errors = 0
        adjacent_key_errors = 0
        same_hand_errors = 0
        other_errors = 0
        
        # Define adjacency matrix (simplified)
        left_hand = "qwertasdfgzxcv"
        right_hand = "yuiophjklnm"
        
        # Analyze typo clusters
        # This is simplified - a more robust version would use a keyboard layout map
        for pattern in self.typo_patterns:
            p = pattern["pattern"]
            if len(p) >= 2:
                last_char = p[-1]
                second_last_char = p[-2]
                
                if last_char in home_row_keys and second_last_char in home_row_keys:
                    home_row_errors += 1
                # Check if characters are adjacent on keyboard (simplified)
                # A proper implementation would use a keyboard layout map
                elif abs(ord(last_char) - ord(second_last_char)) <= 1:
                    adjacent_key_errors += 1
                # Check if same hand was used
                elif (last_char in left_hand and second_last_char in left_hand) or \
                     (last_char in right_hand and second_last_char in right_hand):
                    same_hand_errors += 1
                else:
                    other_errors += 1
        
        # Save session typo data
        self.session_typo_data = {
            "typo_rate": typo_rate,
            "common_typo_patterns": sorted_patterns,
            "correction_style": {
                "immediate": immediate_corrections,
                "delayed": delayed_corrections
            },
            "typo_clusters": {
                "home_row": home_row_errors,
                "adjacent_keys": adjacent_key_errors,
                "same_hand": same_hand_errors,
                "other": other_errors
            },
            "double_letter_error_rate": double_letter_errors / correction_keystrokes if correction_keystrokes > 0 else 0,
            "inserted_letter_rate": inserted_letter_errors / correction_keystrokes if correction_keystrokes > 0 else 0,
            "missed_letter_rate": missed_letter_errors / correction_keystrokes if correction_keystrokes > 0 else 0,
            "reversed_letters_rate": reversed_letters_errors / correction_keystrokes if correction_keystrokes > 0 else 0
        }
    
    def save_session_data(self):
        """Save the session data to JSON and CSV files"""
        # Create session files
        session_json = os.path.join(self.profile_dir, f"{self.session_id}.json")
        session_csv = os.path.join(self.profile_dir, f"{self.session_id}.csv")
        
        # Save JSON
        with open(session_json, 'w') as f:
            json.dump(self.session_data, f, indent=2)
        
        # Save CSV
        with open(session_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['key', 'keydown_time', 'keyup_time', 'dwell_time', 'flight_time', 'is_correction'])
            for data in self.session_data:
                writer.writerow([
                    data['key'],
                    data['keydown_time'],
                    data['keyup_time'],
                    data['dwell_time'],
                    data['flight_time'],
                    data['is_correction']
                ])
                
        # Also save typo analysis if available after analysis completes
        if hasattr(self, 'session_typo_data'):
            typo_json = os.path.join(self.profile_dir, f"{self.session_id}_typo_analysis.json")
            with open(typo_json, 'w') as f:
                json.dump(self.session_typo_data, f, indent=2)
    
    def update_profile(self):
        """Update the user profile with the new session data"""
        # Calculate dwell times for each key
        dwell_times = {}
        for data in self.session_data:
            key = data['key']
            dwell = data['dwell_time']
            
            if key not in dwell_times:
                dwell_times[key] = []
            dwell_times[key].append(dwell)
        
        # Calculate flight times for each key pair
        flight_times = {}
        for i in range(1, len(self.session_data)):
            prev_key = self.session_data[i-1]['key']
            curr_key = self.session_data[i]['key']
            key_pair = f"{prev_key}→{curr_key}"
            flight = self.session_data[i]['flight_time']
            
            if key_pair not in flight_times:
                flight_times[key_pair] = []
            flight_times[key_pair].append(flight)
        
        # Update profile with new data
        session_count = self.profile['session_count'] + 1
        weight_old = self.profile['session_count'] / session_count if session_count > 1 else 0
        weight_new = 1 / session_count
        
        # Update mean dwell times
        for key, times in dwell_times.items():
            mean_dwell = statistics.mean(times)
            std_dwell = statistics.stdev(times) if len(times) > 1 else 0
            
            if key in self.profile['mean_dwell_times']:
                self.profile['mean_dwell_times'][key] = (
                    self.profile['mean_dwell_times'][key] * weight_old + mean_dwell * weight_new
                )
                
                # Update standard deviation using pooled standard deviation formula
                if session_count > 1:
                    old_std = self.profile['std_dwell_times'].get(key, 0)
                    old_mean = self.profile['mean_dwell_times'][key]
                    new_mean = mean_dwell
                    
                    pooled_var = (
                        (session_count - 1) * (old_std ** 2) + (len(times) - 1) * (std_dwell ** 2) +
                        weight_old * weight_new * (old_mean - new_mean) ** 2
                    ) / (session_count - 1 + len(times) - 1)
                    
                    self.profile['std_dwell_times'][key] = np.sqrt(pooled_var)
                else:
                    self.profile['std_dwell_times'][key] = std_dwell
            else:
                self.profile['mean_dwell_times'][key] = mean_dwell
                self.profile['std_dwell_times'][key] = std_dwell
        
        # Update mean flight times
        for key_pair, times in flight_times.items():
            mean_flight = statistics.mean(times)
            std_flight = statistics.stdev(times) if len(times) > 1 else 0
            
            if key_pair in self.profile['mean_flight_times']:
                self.profile['mean_flight_times'][key_pair] = (
                    self.profile['mean_flight_times'][key_pair] * weight_old + mean_flight * weight_new
                )
                
                # Update standard deviation
                if session_count > 1:
                    old_std = self.profile['std_flight_times'].get(key_pair, 0)
                    old_mean = self.profile['mean_flight_times'][key_pair]
                    new_mean = mean_flight
                    
                    pooled_var = (
                        (session_count - 1) * (old_std ** 2) + (len(times) - 1) * (std_flight ** 2) +
                        weight_old * weight_new * (old_mean - new_mean) ** 2
                    ) / (session_count - 1 + len(times) - 1)
                    
                    self.profile['std_flight_times'][key_pair] = np.sqrt(pooled_var)
                else:
                    self.profile['std_flight_times'][key_pair] = std_flight
            else:
                self.profile['mean_flight_times'][key_pair] = mean_flight
                self.profile['std_flight_times'][key_pair] = std_flight
        
        # Update session count
        self.profile['session_count'] = session_count
        
        # Update typo pattern data if analysis was performed
        if hasattr(self, 'session_typo_data'):
            # Update typo rate with weighted average
            old_typo_rate = self.profile['typo_rate']
            new_typo_rate = self.session_typo_data['typo_rate']
            self.profile['typo_rate'] = old_typo_rate * weight_old + new_typo_rate * weight_new
            
            # Update correction style with weighted average
            for style in ['immediate', 'delayed']:
                old_count = self.profile['correction_style'][style]
                new_count = self.session_typo_data['correction_style'][style]
                self.profile['correction_style'][style] = old_count * weight_old + new_count * weight_new
                
            # Update typo clusters with weighted average
            for cluster in ['home_row', 'adjacent_keys', 'same_hand', 'other']:
                old_count = self.profile['typo_clusters'][cluster]
                new_count = self.session_typo_data['typo_clusters'][cluster]
                self.profile['typo_clusters'][cluster] = old_count * weight_old + new_count * weight_new
                
            # Update error rates with weighted average
            for error_type in ['double_letter_error_rate', 'inserted_letter_rate', 
                              'missed_letter_rate', 'reversed_letters_rate']:
                old_rate = self.profile[error_type]
                new_rate = self.session_typo_data[error_type]
                self.profile[error_type] = old_rate * weight_old + new_rate * weight_new
                
            # Update common typo patterns
            # First merge dictionaries
            common_patterns = self.profile.get('common_typo_patterns', {})
            new_patterns = self.session_typo_data['common_typo_patterns']
            
            for pattern, count in new_patterns.items():
                if pattern in common_patterns:
                    common_patterns[pattern] = common_patterns[pattern] * weight_old + count * weight_new
                else:
                    common_patterns[pattern] = count * weight_new
                    
            # Sort by frequency and keep top 20
            sorted_patterns = {k: v for k, v in sorted(common_patterns.items(), 
                                                      key=lambda item: item[1], 
                                                      reverse=True)[:20]}
            self.profile['common_typo_patterns'] = sorted_patterns
        
        # Save updated profile
        with open(self.profile_file, 'w') as f:
            json.dump(self.profile, f, indent=2)


# GUI for recording
class RecorderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Typing Biometric Recorder")
        self.root.geometry("500x400")
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # User selection
        ttk.Label(main_frame, text="Select User Profile:").pack(pady=5, anchor=tk.W)
        
        # Get available users
        self.users = self.get_available_users()
        if not self.users:
            self.users = ["user1", "user2"]  # Default users
        
        self.user_var = tk.StringVar(value=self.users[0])
        user_combo = ttk.Combobox(main_frame, textvariable=self.user_var, values=self.users)
        user_combo.pack(pady=5, fill=tk.X)
        
        # Create new user
        ttk.Label(main_frame, text="Or Create New User:").pack(pady=5, anchor=tk.W)
        user_frame = ttk.Frame(main_frame)
        user_frame.pack(pady=5, fill=tk.X)
        
        self.new_user_var = tk.StringVar()
        new_user_entry = ttk.Entry(user_frame, textvariable=self.new_user_var)
        new_user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        create_user_btn = ttk.Button(user_frame, text="Create", command=self.create_user)
        create_user_btn.pack(side=tk.RIGHT)
        
        # Text area for typing
        ttk.Label(main_frame, text="Type Text Here (when recording):").pack(pady=(20, 5), anchor=tk.W)
        
        self.text_area = tk.Text(main_frame, height=8, width=50, state=tk.DISABLED)
        self.text_area.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10, fill=tk.X)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Recording", command=self.start_recording)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Recording", command=self.stop_recording, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(pady=5, anchor=tk.W)
        
        # Recorder instance
        self.recorder = None
    
    def get_available_users(self):
        """Get list of available user profiles"""
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
        return [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
    
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
        self.users.append(new_user)
        self.user_var.set(new_user)
        messagebox.showinfo("Success", f"User profile '{new_user}' created")
        
        # Clear entry
        self.new_user_var.set("")
    
    def start_recording(self):
        """Start recording typing biometrics"""
        user_id = self.user_var.get()
        if not user_id:
            messagebox.showerror("Error", "Please select a user profile")
            return
            
        self.recorder = TypingRecorder(user_id)
        self.recorder.start_recording()
        
        # Update UI
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set(f"Recording typing for user '{user_id}'...")
    
    def stop_recording(self):
        """Stop recording typing biometrics"""
        if self.recorder:
            self.recorder.stop_recording()
            
        # Update UI
        self.text_area.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Recording stopped. Profile updated with typo patterns.")


def main():
    root = tk.Tk()
    app = RecorderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 