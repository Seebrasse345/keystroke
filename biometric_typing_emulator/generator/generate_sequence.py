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
                    # Get how many characters to type before correcting
                    delay = random.randint(1, 3)
                    # Add after some delay - will need to add multiple backspaces
                    new_sequence.insert(error_pos + 1, double_data)
                    
                    # Add backspaces after the delay
                    insert_pos = error_pos + 1 + delay
                    if insert_pos < len(new_sequence):
                        for i in range(delay + 1):  # +1 to delete the extra char too
                            bs_data = {
                                "key": "backspace", 
                                "dwell": self.get_dwell_time("backspace"),
                                "flight": self.get_flight_time(
                                    "backspace" if i > 0 else new_sequence[insert_pos - 1]["key"], 
                                    "backspace"
                                ),
                                "is_correction": 1
                            }
                            new_sequence.insert(insert_pos + i, bs_data)
                        
                        # Re-add the correct sequence of keys
                        for i in range(delay):
                            if error_pos + 1 + i < len(sequence):
                                orig_key = sequence[error_pos + 1 + i]["key"]
                                key_data = {
                                    "key": orig_key,
                                    "dwell": self.get_dwell_time(orig_key),
                                    "flight": self.get_flight_time(
                                        "backspace" if i == 0 else new_sequence[insert_pos + delay + i - 1]["key"],
                                        orig_key
                                    )
                                }
                                new_sequence.insert(insert_pos + delay + 1 + i, key_data)
                
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
                    # Delayed correction
                    delay = random.randint(1, 3)
                    new_sequence.insert(error_pos, typo_data)
                    
                    # Add backspaces after the delay
                    insert_pos = error_pos + 1 + delay
                    if insert_pos < len(new_sequence):
                        for i in range(delay + 1):  # +1 to delete the inserted char too
                            bs_data = {
                                "key": "backspace",
                                "dwell": self.get_dwell_time("backspace"),
                                "flight": self.get_flight_time(
                                    "backspace" if i > 0 else new_sequence[insert_pos - 1]["key"],
                                    "backspace"
                                ),
                                "is_correction": 1
                            }
                            new_sequence.insert(insert_pos + i, bs_data)
                        
                        # Re-add the correct sequence
                        for i in range(delay):
                            if error_pos + i < len(sequence):
                                orig_key = sequence[error_pos + i]["key"]
                                key_data = {
                                    "key": orig_key,
                                    "dwell": self.get_dwell_time(orig_key),
                                    "flight": self.get_flight_time(
                                        "backspace" if i == 0 else new_sequence[insert_pos + delay + i - 1]["key"],
                                        orig_key
                                    )
                                }
                                new_sequence.insert(insert_pos + delay + 1 + i, key_data)
                
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
                        # Delayed correction - notice after a few more characters
                        delay = random.randint(1, 3)
                        insert_pos = error_pos + 1 + delay
                        
                        if insert_pos < len(new_sequence):
                            # Add backspaces for all typed chars (including the one after missed)
                            for i in range(delay + 1):
                                bs_data = {
                                    "key": "backspace",
                                    "dwell": self.get_dwell_time("backspace"),
                                    "flight": self.get_flight_time(
                                        "backspace" if i > 0 else new_sequence[insert_pos - 1]["key"],
                                        "backspace"
                                    ),
                                    "is_correction": 1
                                }
                                new_sequence.insert(insert_pos + i, bs_data)
                            
                            # Re-add the correct sequence including missed char
                            # First add the missed char
                            missed_data = {
                                "key": missed_key,
                                "dwell": self.get_dwell_time(missed_key),
                                "flight": self.get_flight_time("backspace", missed_key)
                            }
                            new_sequence.insert(insert_pos + delay + 1, missed_data)
                            
                            # Then add all the chars that were backspaced
                            for i in range(delay + 1):
                                if error_pos + i < len(sequence):
                                    orig_key = sequence[error_pos + i]["key"]
                                    prev_key = missed_key if i == 0 else new_sequence[insert_pos + delay + 1 + i - 1]["key"]
                                    key_data = {
                                        "key": orig_key,
                                        "dwell": self.get_dwell_time(orig_key),
                                        "flight": self.get_flight_time(prev_key, orig_key)
                                    }
                                    new_sequence.insert(insert_pos + delay + 2 + i, key_data)
                
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
                        # Delay the correction
                        delay = random.randint(1, 2)  # Smaller delay for reversal errors
                        
                        # Replace the original keys with the swapped version
                        new_sequence[error_pos] = swap1_data
                        new_sequence.insert(error_pos + 1, swap2_data)
                        
                        # Calculate position to insert correction
                        insert_pos = error_pos + 2 + delay
                        
                        if insert_pos < len(new_sequence):
                            # Add backspaces for everything from the error until correction point
                            for i in range(delay + 2):
                                bs_data = {
                                    "key": "backspace",
                                    "dwell": self.get_dwell_time("backspace"),
                                    "flight": self.get_flight_time(
                                        "backspace" if i > 0 else new_sequence[insert_pos - 1]["key"],
                                        "backspace"
                                    ),
                                    "is_correction": 1
                                }
                                new_sequence.insert(insert_pos + i, bs_data)
                            
                            # Re-add the correct sequence
                            # First the originally swapped pair in correct order
                            corr1_data["flight"] = self.get_flight_time("backspace", curr_key)
                            new_sequence.insert(insert_pos + delay + 2, corr1_data)
                            new_sequence.insert(insert_pos + delay + 3, corr2_data)
                            
                            # Then any additional characters that were backspaced
                            for i in range(delay):
                                if error_pos + 2 + i < len(sequence):
                                    orig_key = sequence[error_pos + 2 + i]["key"]
                                    prev_key = next_key if i == 0 else new_sequence[insert_pos + delay + 4 + i - 1]["key"]
                                    key_data = {
                                        "key": orig_key,
                                        "dwell": self.get_dwell_time(orig_key),
                                        "flight": self.get_flight_time(prev_key, orig_key)
                                    }
                                    new_sequence.insert(insert_pos + delay + 4 + i, key_data)
        
        return new_sequence
    
    def generate_sequence(self, text, add_pauses=True, add_corrections=True):
        """Generate a typing sequence for the provided text"""
        sequence = []
        
        for i, char in enumerate(text):
            # Get dwell time for this character
            dwell_time = self.get_dwell_time(char)
            
            # Get flight time from previous character
            flight_time = 0
            if i > 0:
                prev_char = text[i-1]
                flight_time = self.get_flight_time(prev_char, char)
            
            # Add to sequence
            char_data = {
                "key": char,
                "dwell": dwell_time,
                "flight": flight_time,
                "is_correction": 0
            }
            sequence.append(char_data)
        
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