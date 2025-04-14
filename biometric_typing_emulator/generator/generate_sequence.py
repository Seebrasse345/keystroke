import json
import os
import random
import numpy as np
import time

class TypingSequenceGenerator:
    def __init__(self, user_id):
        self.user_id = user_id
        self.profile_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "profiles", 
            user_id, 
            f"{user_id}_profile.json"
        )
        self.load_profile()
        
    def load_profile(self):
        """Load the user profile from file"""
        if not os.path.exists(self.profile_path):
            raise FileNotFoundError(f"Profile for user {self.user_id} not found at {self.profile_path}")
            
        with open(self.profile_path, 'r') as f:
            self.profile = json.load(f)
            
        # Check if profile has required data
        if not self.profile.get("mean_dwell_times") or not self.profile.get("mean_flight_times"):
            raise ValueError(f"Profile for user {self.user_id} is incomplete. Please record more typing data.")
    
    def get_dwell_time(self, key):
        """Get a realistic dwell time for a key based on profile data"""
        if key in self.profile["mean_dwell_times"]:
            mean_dwell = self.profile["mean_dwell_times"][key]
            std_dwell = self.profile["std_dwell_times"].get(key, mean_dwell * 0.1)  # Default 10% of mean if no std
            
            # Generate a random value using normal distribution
            dwell_time = np.random.normal(mean_dwell, std_dwell)
            
            # Ensure dwell time is not negative
            return max(10, dwell_time)
        else:
            # If key not in profile, use average of all keys or a default value
            all_dwells = list(self.profile["mean_dwell_times"].values())
            if all_dwells:
                avg_dwell = sum(all_dwells) / len(all_dwells)
                return max(10, np.random.normal(avg_dwell, avg_dwell * 0.1))
            else:
                # Default values if no data available
                return random.uniform(50, 100)
    
    def get_flight_time(self, prev_key, curr_key):
        """Get a realistic flight time between two keys based on profile data"""
        key_pair = f"{prev_key}→{curr_key}"
        
        if key_pair in self.profile["mean_flight_times"]:
            mean_flight = self.profile["mean_flight_times"][key_pair]
            std_flight = self.profile["std_flight_times"].get(key_pair, mean_flight * 0.15)  # Default 15% of mean
            
            # Generate a random value using normal distribution
            flight_time = np.random.normal(mean_flight, std_flight)
            
            # Ensure flight time is not negative
            return max(5, flight_time)
        else:
            # If key pair not in profile, use average of all flight times or a default value
            all_flights = list(self.profile["mean_flight_times"].values())
            if all_flights:
                avg_flight = sum(all_flights) / len(all_flights)
                return max(5, np.random.normal(avg_flight, avg_flight * 0.15))
            else:
                # Default values if no data available
                return random.uniform(80, 150)
    
    def get_typo_probability(self):
        """Get the probability of making a typo based on user's profile"""
        # If typo rate is present in profile, use it
        if "typo_rate" in self.profile:
            return self.profile["typo_rate"]
        # Otherwise use default
        return 0.03  # 3% default typo rate
    
    def get_typo_type_distribution(self):
        """Get the distribution of typo types based on user's profile"""
        # If typo type distributions are present in profile
        if all(key in self.profile for key in ["double_letter_error_rate", "inserted_letter_rate", 
                                              "missed_letter_rate", "reversed_letters_rate"]):
            # Get the rates from profile
            double_letter = max(0.001, self.profile["double_letter_error_rate"])
            inserted = max(0.001, self.profile["inserted_letter_rate"])  
            missed = max(0.001, self.profile["missed_letter_rate"])
            reversed_letters = max(0.001, self.profile["reversed_letters_rate"])
            
            # Normalize to sum to 1.0
            total = double_letter + inserted + missed + reversed_letters
            return {
                "double_letter": double_letter / total,
                "inserted": inserted / total,
                "missed": missed / total,
                "reversed": reversed_letters / total
            }
        
        # Default distribution
        return {
            "double_letter": 0.4,
            "inserted": 0.3,
            "missed": 0.2,
            "reversed": 0.1
        }
    
    def choose_typo_cluster(self):
        """Choose a typo cluster based on user's profile"""
        if "typo_clusters" in self.profile:
            clusters = self.profile["typo_clusters"]
            # Convert to probabilities
            home_row = max(0.001, clusters["home_row"])
            adjacent_keys = max(0.001, clusters["adjacent_keys"])
            same_hand = max(0.001, clusters["same_hand"])
            other = max(0.001, clusters["other"])
            
            # Normalize to sum to 1.0
            total = home_row + adjacent_keys + same_hand + other
            probs = [
                home_row / total,
                adjacent_keys / total,
                same_hand / total,
                other / total
            ]
            
            # Choose a cluster
            return random.choices(
                ["home_row", "adjacent_keys", "same_hand", "other"],
                weights=probs,
                k=1
            )[0]
            
        # Default is randomly chosen
        return random.choice(["home_row", "adjacent_keys", "same_hand", "other"])
    
    def get_typical_error_for_key(self, key, error_type):
        """Get a typical error character for a given key based on error type and user patterns"""
        # Define keyboard layout and relationships
        home_row = "asdfghjkl;"
        qwerty_rows = [
            "1234567890-=",
            "qwertyuiop[]\\",
            "asdfghjkl;'",
            "zxcvbnm,./"
        ]
        
        left_hand = "qwertasdfgzxcv"
        right_hand = "yuiophjklnm"
        
        # Find position of key in layout
        key_row, key_col = -1, -1
        for row_idx, row in enumerate(qwerty_rows):
            if key in row:
                key_row = row_idx
                key_col = row.index(key)
                break
        
        # Check common typo patterns from user profile
        common_typos = self.profile.get("common_typo_patterns", {})
        
        # Look for patterns that end with the target key for potential typo sources
        for pattern, freq in common_typos.items():
            if len(pattern) >= 2 and pattern[-1] == key:
                # There's a chance to replace this pattern with a known error
                if random.random() < 0.6:  # 60% chance to use a known pattern
                    return pattern[-2]  # Use the character that typically precedes the key
        
        # If we don't have a common pattern, use layout-based logic
        if error_type == "double_letter":
            # Simply duplicate the key
            return key
            
        elif error_type == "adjacent_keys" or error_type == "inserted":
            # Find adjacent keys on the keyboard
            if key_row >= 0 and key_col >= 0:
                adjacent_chars = []
                
                # Same row, adjacent columns
                if key_col > 0:
                    adjacent_chars.append(qwerty_rows[key_row][key_col - 1])
                if key_col < len(qwerty_rows[key_row]) - 1:
                    adjacent_chars.append(qwerty_rows[key_row][key_col + 1])
                    
                # Row above, same/adjacent columns
                if key_row > 0:
                    for c in range(max(0, key_col - 1), min(len(qwerty_rows[key_row - 1]), key_col + 2)):
                        adjacent_chars.append(qwerty_rows[key_row - 1][c])
                        
                # Row below, same/adjacent columns
                if key_row < len(qwerty_rows) - 1:
                    for c in range(max(0, key_col - 1), min(len(qwerty_rows[key_row + 1]), key_col + 2)):
                        adjacent_chars.append(qwerty_rows[key_row + 1][c])
                
                if adjacent_chars:
                    return random.choice(adjacent_chars)
            
            # Fallback for keys not found in layout
            return random.choice("qwertyuiopasdfghjklzxcvbnm")
            
        elif error_type == "same_hand":
            # Error with a key typed by same hand
            if key in left_hand:
                return random.choice(left_hand)
            elif key in right_hand:
                return random.choice(right_hand)
            else:
                return random.choice("qwertyuiopasdfghjklzxcvbnm")
                
        elif error_type == "reversed":
            # This would require context of surrounding keys
            # For simplicity, just return the key (caller will handle reversing)
            return key
            
        else:  # Default/other
            return random.choice("qwertyuiopasdfghjklzxcvbnm")
            
    def should_make_immediate_correction(self):
        """Determine if this user typically makes immediate corrections or continues typing"""
        if "correction_style" in self.profile:
            immediate = self.profile["correction_style"]["immediate"]
            delayed = self.profile["correction_style"]["delayed"]
            
            # Calculate probability of immediate correction
            if immediate + delayed > 0:
                immediate_prob = immediate / (immediate + delayed)
                return random.random() < immediate_prob
        
        # Default behavior (80% immediate corrections)
        return random.random() < 0.8
    
    def add_realistic_corrections(self, text, sequence):
        """Add realistic typing errors and corrections based on user's profile"""
        if len(text) < 10 or len(sequence) < 10:
            return sequence  # Too short to add errors
            
        # Get user's typo rate
        typo_rate = self.get_typo_probability()
        
        # Get distribution of typo types for this user
        typo_types = self.get_typo_type_distribution()
        
        # Make a copy of the sequence
        new_sequence = sequence.copy()
        
        # Expected number of typos based on text length and user's typo rate
        n_typos = max(1, int(len(text) * typo_rate))
        
        # Create a list of potential error positions
        # Avoid very beginning and very end of text
        potential_positions = list(range(3, len(new_sequence) - 3))
        
        # Shuffle positions to avoid clustering
        random.shuffle(potential_positions)
        
        # Limit to expected number of typos
        error_positions = potential_positions[:n_typos]
        error_positions.sort()  # Put back in order
        
        # Apply typos at each position
        for error_pos in error_positions:
            # Don't insert errors too close to previous ones
            if error_pos < 3:
                continue
                
            # Select error type based on user's distribution
            error_type = random.choices(
                ["double_letter", "inserted", "missed", "reversed"],
                weights=[
                    typo_types["double_letter"],
                    typo_types["inserted"],
                    typo_types["missed"],
                    typo_types["reversed"]
                ],
                k=1
            )[0]
            
            # Choose error cluster (which keys are likely to be mistyped)
            error_cluster = self.choose_typo_cluster()
            
            # Get the correct key that should be typed
            correct_key = new_sequence[error_pos]["key"]
            
            if error_type == "double_letter":
                # Double letter error - typing the same key twice
                double_key = correct_key
                double_dwell = self.get_dwell_time(double_key)
                double_flight = self.get_flight_time(double_key, double_key)
                
                # Add backspace for correction
                bs_dwell = self.get_dwell_time("backspace")
                bs_flight = self.get_flight_time(double_key, "backspace")
                
                # Insert double character and backspace
                double_data = {"key": double_key, "dwell": double_dwell, "flight": double_flight}
                bs_data = {"key": "backspace", "dwell": bs_dwell, "flight": bs_flight, "is_correction": 1}
                
                # Should this be an immediate correction?
                if self.should_make_immediate_correction():
                    # Add right after the double letter
                    new_sequence.insert(error_pos + 1, double_data)
                    new_sequence.insert(error_pos + 2, bs_data)
                    
                    # Update flight time for next key
                    if error_pos + 3 < len(new_sequence):
                        next_key = new_sequence[error_pos + 3]["key"]
                        new_sequence[error_pos + 3]["flight"] = self.get_flight_time("backspace", next_key)
                else:
                    # --- Refactored Delayed Correction for double_letter ---
                    delay = random.randint(1, 3)
                    insert_pos_error = error_pos + 1 # Position after the original correct key

                    # 1. Insert the duplicated character
                    double_data = {"key": double_key, "dwell": double_dwell, "flight": double_flight}
                    new_sequence.insert(insert_pos_error, double_data)
                    
                    # Calculate how many characters were typed *after* the error was inserted
                    effective_delay = 0
                    original_indices_to_retype = []
                    for i in range(delay):
                        original_delayed_index = error_pos + 1 + i
                        if original_delayed_index < len(sequence):
                           effective_delay += 1
                           original_indices_to_retype.append(original_delayed_index)
                        else:
                           break # Stop if we reach the end of the original sequence

                    # 2. Calculate where the correction (backspaces) should start
                    correction_start_index = insert_pos_error + effective_delay

                    # 3. Insert Backspaces
                    # Need to backspace over the 'effective_delay' characters + the duplicated char
                    num_backspaces = effective_delay + 1
                    # Get the key immediately before the first backspace will be inserted
                    key_before_first_bs = new_sequence[correction_start_index - 1]["key"]

                    for i in range(num_backspaces):
                        bs_flight_current = self.get_flight_time(
                            "backspace" if i > 0 else key_before_first_bs, # Flight from prev char or prev BS
                            "backspace"
                        )
                        bs_data = {
                            "key": "backspace",
                            "dwell": self.get_dwell_time("backspace"),
                            "flight": bs_flight_current,
                            "is_correction": 1
                        }
                        # Insert BS at the correction point, pushing subsequent elements rightward
                        new_sequence.insert(correction_start_index + i, bs_data)

                    # 4. Re-type the original characters that were typed during the delay
                    retype_start_index = correction_start_index + num_backspaces
                    last_key_before_retype = "backspace" # First retyped key follows the last backspace

                    for original_index in original_indices_to_retype:
                        orig_key_data = sequence[original_index]
                        orig_key = orig_key_data["key"]

                        retype_flight = self.get_flight_time(last_key_before_retype, orig_key)
                        retype_dwell = self.get_dwell_time(orig_key) # Use profile dwell time

                        key_data = {
                            "key": orig_key,
                            "dwell": retype_dwell,
                            "flight": retype_flight,
                            "is_correction": 0 # It's part of the intended sequence being retyped
                        }
                        # Insert the re-typed key at the current end of the correction block
                        new_sequence.insert(retype_start_index, key_data)
                        retype_start_index += 1 # Move insertion point for the next re-typed key
                        last_key_before_retype = orig_key # Update for next flight time calc

                    # 5. Update flight time for the key immediately following the entire correction block
                    final_corrected_index = retype_start_index # This is now the index of the next char
                    if final_corrected_index < len(new_sequence):
                        next_key_after_correction = new_sequence[final_corrected_index]["key"]
                        # The last key typed was the last re-typed character
                        last_typed_key = new_sequence[final_corrected_index - 1]["key"]
                        new_sequence[final_corrected_index]["flight"] = self.get_flight_time(last_typed_key, next_key_after_correction)
                    # --- End Refactored Delayed Correction ---

            elif error_type == "inserted":
                # Inserted key error - adding an extra key
                # Get a typical error key for this character
                typo_key = self.get_typical_error_for_key(correct_key, error_cluster)
                typo_dwell = self.get_dwell_time(typo_key)
                typo_flight = self.get_flight_time(new_sequence[error_pos - 1]["key"], typo_key)
                
                # Add backspace for correction
                bs_dwell = self.get_dwell_time("backspace")
                bs_flight = self.get_flight_time(typo_key, "backspace")
                
                # Insert typo and backspace
                typo_data = {"key": typo_key, "dwell": typo_dwell, "flight": typo_flight}
                bs_data = {"key": "backspace", "dwell": bs_dwell, "flight": bs_flight, "is_correction": 1}
                
                # Apply correction based on user style
                if self.should_make_immediate_correction():
                    new_sequence.insert(error_pos, typo_data)
                    new_sequence.insert(error_pos + 1, bs_data)
                    
                    # Update flight time for correct key
                    new_sequence[error_pos + 2]["flight"] = self.get_flight_time("backspace", correct_key)
                else:
                    # --- Refactored Delayed Correction for inserted ---
                    delay = random.randint(1, 3)
                    insert_pos_error = error_pos # Position where the typo is inserted

                    # 1. Insert the typo character
                    typo_data = {"key": typo_key, "dwell": typo_dwell, "flight": typo_flight}
                    new_sequence.insert(insert_pos_error, typo_data)

                    # Calculate effective delay and original indices
                    effective_delay = 0
                    original_indices_to_retype = []
                    # The original characters typed during delay start from the original error_pos
                    for i in range(delay):
                        original_delayed_index = error_pos + i
                        if original_delayed_index < len(sequence):
                            effective_delay += 1
                            original_indices_to_retype.append(original_delayed_index)
                        else:
                            break

                    # 2. Calculate where correction (backspaces) starts
                    # It's after the inserted typo and the delayed characters
                    correction_start_index = insert_pos_error + 1 + effective_delay # +1 for the inserted typo

                    # 3. Insert Backspaces
                    # Need to backspace over 'effective_delay' characters + the inserted typo
                    num_backspaces = effective_delay + 1
                    key_before_first_bs = new_sequence[correction_start_index - 1]["key"]

                    for i in range(num_backspaces):
                        bs_flight_current = self.get_flight_time(
                            "backspace" if i > 0 else key_before_first_bs,
                            "backspace"
                        )
                        bs_data = {
                            "key": "backspace",
                            "dwell": self.get_dwell_time("backspace"),
                            "flight": bs_flight_current,
                            "is_correction": 1
                        }
                        new_sequence.insert(correction_start_index + i, bs_data)

                    # 4. Re-type the original characters typed during the delay
                    retype_start_index = correction_start_index + num_backspaces
                    last_key_before_retype = "backspace"

                    # 4a. Re-type the original key that was initially skipped due to the typo
                    # Calculate timing relative to the last backspace
                    correct_key_retype_flight = self.get_flight_time(last_key_before_retype, correct_key)
                    correct_key_retype_dwell = self.get_dwell_time(correct_key)
                    correct_key_data = {
                        "key": correct_key,
                        "dwell": correct_key_retype_dwell,
                        "flight": correct_key_retype_flight,
                        "is_correction": 0
                    }
                    new_sequence.insert(retype_start_index, correct_key_data)
                    retype_start_index += 1
                    last_key_before_retype = correct_key # Update for next potential retype

                    # 4b. Re-type the original characters typed during the delay (if any)
                    for original_index in original_indices_to_retype:
                        orig_key_data = sequence[original_index]
                        orig_key = orig_key_data["key"]

                        retype_flight = self.get_flight_time(last_key_before_retype, orig_key)
                        retype_dwell = self.get_dwell_time(orig_key)

                        key_data = {
                            "key": orig_key,
                            "dwell": retype_dwell,
                            "flight": retype_flight,
                            "is_correction": 0
                        }
                        new_sequence.insert(retype_start_index, key_data)
                        retype_start_index += 1
                        last_key_before_retype = orig_key

                    # 5. Update flight time for the key following the correction block
                    final_corrected_index = retype_start_index
                    if final_corrected_index < len(new_sequence):
                        next_key_after_correction = new_sequence[final_corrected_index]["key"]
                        last_typed_key = new_sequence[final_corrected_index - 1]["key"]
                        new_sequence[final_corrected_index]["flight"] = self.get_flight_time(last_typed_key, next_key_after_correction)
                    # --- End Refactored Delayed Correction ---

            elif error_type == "missed":
                # Missed key error - skipping a character, then realizing later
                if error_pos + 1 < len(new_sequence):
                    # Get keys involved
                    missed_key = correct_key
                    next_key = new_sequence[error_pos + 1]["key"]
                    
                    # Skip this key by adjusting flight time
                    new_sequence[error_pos + 1]["flight"] = self.get_flight_time(new_sequence[error_pos - 1]["key"], next_key)
                    
                    # Decide when to correct based on user style
                    if self.should_make_immediate_correction():
                        # Immediately notice and correct
                        bs_dwell = self.get_dwell_time("backspace")
                        bs_flight = self.get_flight_time(next_key, "backspace")
                        
                        # Add missed character
                        missed_dwell = self.get_dwell_time(missed_key)
                        missed_flight = self.get_flight_time("backspace", missed_key)
                        
                        # Add next character again
                        next_dwell = self.get_dwell_time(next_key)
                        next_flight = self.get_flight_time(missed_key, next_key)
                        
                        # Insert correction sequence
                        bs_data = {"key": "backspace", "dwell": bs_dwell, "flight": bs_flight, "is_correction": 1}
                        missed_data = {"key": missed_key, "dwell": missed_dwell, "flight": missed_flight}
                        next_data = {"key": next_key, "dwell": next_dwell, "flight": next_flight}
                        
                        new_sequence.insert(error_pos + 2, bs_data)
                        new_sequence.insert(error_pos + 3, missed_data)
                        new_sequence.insert(error_pos + 4, next_data)
                        
                        # Update flight time for next key
                        if error_pos + 5 < len(new_sequence):
                            next_next_key = new_sequence[error_pos + 5]["key"]
                            new_sequence[error_pos + 5]["flight"] = self.get_flight_time(next_key, next_next_key)
                    else:
                        # --- Refactored Delayed Correction for missed ---
                        delay = random.randint(1, 3)
                        # The "error" is skipping sequence[error_pos]
                        # Typing starts immediately with sequence[error_pos + 1]
                        
                        # Calculate effective delay and original indices to retype
                        # The characters typed during the delay start *after* the missed key's position
                        effective_delay = 0
                        original_indices_to_retype = [] 
                        for i in range(delay):
                             # These are the indices of the characters typed *after* the missed one, during the delay
                            original_delayed_index = error_pos + 1 + i
                            if original_delayed_index < len(sequence):
                                effective_delay += 1
                                # We need to retype these AND the missed key eventually
                                original_indices_to_retype.append(original_delayed_index) 
                            else:
                                break
                        
                        # 1. Adjust flight time for the key immediately after the (initially) missed key
                        # This happens *before* the delay and correction are added
                        if error_pos > 0 and error_pos + 1 < len(new_sequence):
                             key_before_missed = new_sequence[error_pos - 1]["key"]
                             key_after_missed = new_sequence[error_pos + 1]["key"] # Key that was typed instead of the missed one
                             new_sequence[error_pos + 1]["flight"] = self.get_flight_time(key_before_missed, key_after_missed)
                        
                        # Remove the original missed key data point from new_sequence TEMPORARILY.
                        # It simplifies indexing for the correction insertion. We add it back during retyping.
                        # We know its original index was error_pos.
                        # Note: Removing elements shifts indices of subsequent elements left by 1.
                        del new_sequence[error_pos] 

                        # 2. Calculate where correction starts. It's after the delayed characters.
                        # Since we deleted the missed key at error_pos, the delayed keys now start at error_pos.
                        correction_start_index = error_pos + effective_delay

                        # 3. Insert Backspaces
                        # Need to backspace over the 'effective_delay' characters that were typed *after* the missed position.
                        num_backspaces = effective_delay
                        if num_backspaces == 0: continue # Should not happen based on effective_delay check, but safe guard
                        
                        key_before_first_bs = new_sequence[correction_start_index - 1]["key"]

                        for i in range(num_backspaces):
                            bs_flight_current = self.get_flight_time(
                                "backspace" if i > 0 else key_before_first_bs,
                                "backspace"
                            )
                            bs_data = {
                                "key": "backspace",
                                "dwell": self.get_dwell_time("backspace"),
                                "flight": bs_flight_current,
                                "is_correction": 1
                            }
                            new_sequence.insert(correction_start_index + i, bs_data)

                        # 4. Re-add the correct sequence: the missed key + the delayed keys
                        retype_start_index = correction_start_index + num_backspaces
                        last_key_before_retype = "backspace"

                        # 4a. Insert the originally missed key first
                        missed_key_data = sequence[error_pos] # Get original data for missed key
                        missed_key = missed_key_data["key"]
                        missed_dwell = self.get_dwell_time(missed_key)
                        missed_flight = self.get_flight_time(last_key_before_retype, missed_key)
                        
                        corrected_missed_data = {
                            "key": missed_key,
                            "dwell": missed_dwell,
                            "flight": missed_flight,
                            "is_correction": 0 # Part of the corrected sequence
                        }
                        new_sequence.insert(retype_start_index, corrected_missed_data)
                        retype_start_index += 1
                        last_key_before_retype = missed_key # Update for next flight time

                        # 4b. Insert the original characters typed during the delay
                        for original_index in original_indices_to_retype:
                            orig_key_data = sequence[original_index]
                            orig_key = orig_key_data["key"]

                            retype_flight = self.get_flight_time(last_key_before_retype, orig_key)
                            retype_dwell = self.get_dwell_time(orig_key)

                            key_data = {
                                "key": orig_key,
                                "dwell": retype_dwell,
                                "flight": retype_flight,
                                "is_correction": 0
                            }
                            new_sequence.insert(retype_start_index, key_data)
                            retype_start_index += 1
                            last_key_before_retype = orig_key
                        
                        # 5. Update flight time for the key following the correction block
                        final_corrected_index = retype_start_index
                        if final_corrected_index < len(new_sequence):
                            next_key_after_correction = new_sequence[final_corrected_index]["key"]
                            last_typed_key = new_sequence[final_corrected_index - 1]["key"]
                            new_sequence[final_corrected_index]["flight"] = self.get_flight_time(last_typed_key, next_key_after_correction)
                        # --- End Refactored Delayed Correction ---

            elif error_type == "reversed":
                # Reversed keys error - typing two characters in the wrong order
                if error_pos + 1 < len(new_sequence):
                    curr_key = correct_key
                    next_key = new_sequence[error_pos + 1]["key"]
                    
                    # Create swapped sequence
                    swap1_dwell = self.get_dwell_time(next_key)
                    swap1_flight = self.get_flight_time(new_sequence[error_pos - 1]["key"], next_key)
                    
                    swap2_dwell = self.get_dwell_time(curr_key)
                    swap2_flight = self.get_flight_time(next_key, curr_key)
                    
                    # Create backspace corrections
                    bs1_dwell = self.get_dwell_time("backspace")
                    bs1_flight = self.get_flight_time(curr_key, "backspace")
                    
                    bs2_dwell = self.get_dwell_time("backspace")
                    bs2_flight = self.get_flight_time("backspace", "backspace")
                    
                    # Create correct sequence
                    corr1_dwell = self.get_dwell_time(curr_key)
                    corr1_flight = self.get_flight_time("backspace", curr_key)
                    
                    corr2_dwell = self.get_dwell_time(next_key)
                    corr2_flight = self.get_flight_time(curr_key, next_key)
                    
                    # Data objects
                    swap1_data = {"key": next_key, "dwell": swap1_dwell, "flight": swap1_flight}
                    swap2_data = {"key": curr_key, "dwell": swap2_dwell, "flight": swap2_flight}
                    
                    bs1_data = {"key": "backspace", "dwell": bs1_dwell, "flight": bs1_flight, "is_correction": 1}
                    bs2_data = {"key": "backspace", "dwell": bs2_dwell, "flight": bs2_flight, "is_correction": 1}
                    
                    corr1_data = {"key": curr_key, "dwell": corr1_dwell, "flight": corr1_flight}
                    corr2_data = {"key": next_key, "dwell": corr2_dwell, "flight": corr2_flight}
                    
                    # Should correction be immediate or delayed?
                    if self.should_make_immediate_correction():
                        # Immediately notice and fix
                        new_sequence[error_pos] = swap1_data  # Replace current key with next key (swap)
                        new_sequence.insert(error_pos + 1, swap2_data)  # Insert current key after it
                        
                        # Insert backspaces
                        new_sequence.insert(error_pos + 2, bs1_data)
                        new_sequence.insert(error_pos + 3, bs2_data)
                        
                        # Insert corrections
                        new_sequence.insert(error_pos + 4, corr1_data)
                        new_sequence.insert(error_pos + 5, corr2_data)
                        
                        # Update subsequent flight time if needed
                        if error_pos + 6 < len(new_sequence):
                            next_next_key = new_sequence[error_pos + 6]["key"]
                            new_sequence[error_pos + 6]["flight"] = self.get_flight_time(next_key, next_next_key)
                    else:
                        # --- Refactored Delayed Correction for reversed ---
                        delay = random.randint(1, 2) # Smaller delay for reversal errors
                        
                        # The error involves replacing sequence[error_pos] and sequence[error_pos+1]
                        # with the swapped versions.
                        if error_pos + 1 >= len(sequence): continue # Need two keys to reverse

                        curr_key_orig_data = sequence[error_pos]
                        next_key_orig_data = sequence[error_pos + 1]
                        curr_key = curr_key_orig_data["key"]
                        next_key = next_key_orig_data["key"]

                        # 1. Apply the reversed typing error to new_sequence
                        # Calculate timings for the swapped keys
                        key_before_swap = new_sequence[error_pos - 1]["key"]
                        swap1_dwell = self.get_dwell_time(next_key) # Dwell of the key typed first (next_key)
                        swap1_flight = self.get_flight_time(key_before_swap, next_key)
                        swap2_dwell = self.get_dwell_time(curr_key) # Dwell of the key typed second (curr_key)
                        swap2_flight = self.get_flight_time(next_key, curr_key)

                        swap1_data = {"key": next_key, "dwell": swap1_dwell, "flight": swap1_flight, "is_correction": 0}
                        swap2_data = {"key": curr_key, "dwell": swap2_dwell, "flight": swap2_flight, "is_correction": 0}

                        # Replace the original two keys with the swapped pair
                        new_sequence[error_pos] = swap1_data
                        new_sequence[error_pos + 1] = swap2_data

                        # Recalculate flight time for the key *after* the swapped pair, if it exists
                        if error_pos + 2 < len(new_sequence):
                            key_after_swap = new_sequence[error_pos + 2]["key"]
                            new_sequence[error_pos + 2]["flight"] = self.get_flight_time(curr_key, key_after_swap)


                        # Calculate effective delay and indices for characters typed *after* the swap
                        effective_delay = 0
                        original_indices_to_retype = []
                        for i in range(delay):
                            # Indices relative to the original sequence, after the reversed pair
                            original_delayed_index = error_pos + 2 + i 
                            if original_delayed_index < len(sequence):
                                effective_delay += 1
                                original_indices_to_retype.append(original_delayed_index)
                            else:
                                break
                        
                        # 2. Calculate where correction starts
                        # It's after the swapped pair and the delayed characters
                        correction_start_index = error_pos + 2 + effective_delay

                        # 3. Insert Backspaces
                        # Need to backspace over 'effective_delay' characters + the swapped pair (2 chars)
                        num_backspaces = effective_delay + 2
                        key_before_first_bs = new_sequence[correction_start_index - 1]["key"]

                        for i in range(num_backspaces):
                            bs_flight_current = self.get_flight_time(
                                "backspace" if i > 0 else key_before_first_bs,
                                "backspace"
                            )
                            bs_data = {
                                "key": "backspace",
                                "dwell": self.get_dwell_time("backspace"),
                                "flight": bs_flight_current,
                                "is_correction": 1
                            }
                            new_sequence.insert(correction_start_index + i, bs_data)

                        # 4. Re-type the correct sequence
                        retype_start_index = correction_start_index + num_backspaces
                        last_key_before_retype = "backspace"

                        # 4a. Re-type the original pair in the correct order
                        # Use timings from the original sequence data
                        corr1_dwell = self.get_dwell_time(curr_key) # Use profile dwell
                        corr1_flight = self.get_flight_time(last_key_before_retype, curr_key)
                        corr2_dwell = self.get_dwell_time(next_key)
                        corr2_flight = self.get_flight_time(curr_key, next_key)

                        corr1_data = {"key": curr_key, "dwell": corr1_dwell, "flight": corr1_flight, "is_correction": 0}
                        corr2_data = {"key": next_key, "dwell": corr2_dwell, "flight": corr2_flight, "is_correction": 0}

                        new_sequence.insert(retype_start_index, corr1_data)
                        new_sequence.insert(retype_start_index + 1, corr2_data)
                        retype_start_index += 2
                        last_key_before_retype = next_key # Last key of the corrected pair

                        # 4b. Re-type the original characters typed during the delay
                        for original_index in original_indices_to_retype:
                            orig_key_data = sequence[original_index]
                            orig_key = orig_key_data["key"]

                            retype_flight = self.get_flight_time(last_key_before_retype, orig_key)
                            retype_dwell = self.get_dwell_time(orig_key)

                            key_data = {
                                "key": orig_key,
                                "dwell": retype_dwell,
                                "flight": retype_flight,
                                "is_correction": 0
                            }
                            new_sequence.insert(retype_start_index, key_data)
                            retype_start_index += 1
                            last_key_before_retype = orig_key

                        # 5. Update flight time for the key following the correction block
                        final_corrected_index = retype_start_index
                        if final_corrected_index < len(new_sequence):
                            next_key_after_correction = new_sequence[final_corrected_index]["key"]
                            last_typed_key = new_sequence[final_corrected_index - 1]["key"]
                            new_sequence[final_corrected_index]["flight"] = self.get_flight_time(last_typed_key, next_key_after_correction)
                        # --- End Refactored Delayed Correction ---

        return new_sequence
    
    def generate_sequence(self, text, add_pauses=True, add_corrections=True):
        """Generate a typing sequence for the provided text"""
        sequence = []
        prev_key_str = None # Keep track of the previous mapped key

        for i, char in enumerate(text):
            # --- Map special whitespace characters to profile keys --- #
            
            # --- Skip Carriage Return --- #
            if char == '\r':
                continue # Skip carriage return characters entirely
                
            key_str = char # Default to the character itself
            if char == '\t':
                key_str = "tab"
            elif char == '\n':
                key_str = "enter"
            elif char == ' ': # Ensure literal spaces use the "space" key if profile expects it
                # Check if "space" exists in profile, otherwise keep ' '
                if "space" in self.profile["mean_dwell_times"] or \
                   any(f"→space" in k or f"space→" in k for k in self.profile["mean_flight_times"]):
                    key_str = "space"
                # else: keep key_str = ' ' - allows profiles without explicit "space" recording
            # --- End Mapping ---

            dwell_time = self.get_dwell_time(key_str)

            flight_time = 0
            # --- Use previous MAPPED key for flight time --- #
            if prev_key_str is not None: # Check if there WAS a previous key
                flight_time = self.get_flight_time(prev_key_str, key_str) # Use PREVIOUS mapped key

            # --- Safeguard against empty key --- #
            if not key_str:
                 print(f"Warning: Skipping empty key generated from char code {ord(char) if isinstance(char, str) and len(char)==1 else 'N/A'} at index {i}")
                 # We also need to ensure prev_key_str doesn't get updated with an empty string
                 continue # Skip this entry entirely

            char_data = {
                "key": key_str, # Use the mapped key string
                "dwell": dwell_time,
                "flight": flight_time,
                "is_correction": 0
            }
            sequence.append(char_data)
            prev_key_str = key_str # Update previous key tracker for the next iteration

        # No longer needed, pauses are inherent in flight times
        #if add_pauses:
        #    sequence = self.add_realistic_pauses(sequence)
        
        # Add realistic corrections (typos and fixes)
        if add_corrections:
            sequence = self.add_realistic_corrections(text, sequence)
        
        return sequence
    
    def save_sequence(self, sequence, output_path=None):
        """Save the generated sequence to a file"""
        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "typing_sequence.txt"
            )
        
        with open(output_path, 'w') as f:
            f.write("key|dwell|flight\n")
            for data in sequence:
                key = data["key"]
                
                # Handle special keys for AHK
                # Ensure both literal space ' ' and string "space" become {Space}
                if key == "space" or key == ' ':
                    key = "{Space}"
                elif key == "enter":
                    key = "{Enter}"
                elif key == "backspace":
                    key = "{Backspace}"
                elif key == "tab":
                    key = "{Tab}"
                
                # Handle other potential single characters that need bracing in AHK Send
                # (e.g., +, ^, !, #, {, }) - Add more if needed
                elif key in ['+', '^', '!', '#', '{', '}']:
                     key = "{" + key + "}"

                f.write(f"{key}|{int(data['dwell'])}|{int(data['flight'])}\n")
        
        return output_path


def main():
    """Command line interface for the generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate realistic typing sequences")
    parser.add_argument("user_id", help="User profile ID")
    parser.add_argument("text", help="Text to generate typing sequence for")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--no-pauses", action="store_true", help="Disable realistic pauses")
    parser.add_argument("--no-corrections", action="store_true", help="Disable realistic corrections")
    
    args = parser.parse_args()
    
    try:
        generator = TypingSequenceGenerator(args.user_id)
        sequence = generator.generate_sequence(
            args.text,
            add_pauses=not args.no_pauses,
            add_corrections=not args.no_corrections
        )
        output_path = generator.save_sequence(sequence, args.output)
        print(f"Typing sequence saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 