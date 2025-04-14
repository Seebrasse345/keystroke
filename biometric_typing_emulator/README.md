 # Biometric Typing Emulator

A full-stack software suite for recording, analyzing, and replaying human typing behavior with precise biometrics using AutoHotkey for realistic keystroke injection.

## Features

- **Multiple user profiles** - Record and maintain separate typing profiles for different users
- **Cumulative learning** - Each recording session updates the profile with weighted averages
- **Statistical analysis** - Calculates mean and standard deviation for key dwell/flight times
- **Realistic replay** - Uses AutoHotkey to inject OS-level keyboard events with human-like timing
- **GUI interface** - Easy-to-use graphical interface for all functions
- **Anti-detection measures** - Variations in timing, realistic pauses, and occasional typos

## Project Structure

```
/biometric_typing_emulator
├── gui/
│   └── interface.py         # Main Tkinter GUI
├── recorder/
│   └── record_typing.py     # Records typing sessions for a user
├── profiles/
│   └── user1/               # Individual user profiles
│       └── session_001.json # Individual session data
│       └── user1_profile.json # Cumulative profile
│   └── user2/
│       └── ...
├── generator/
│   └── generate_sequence.py # Generates typing sequence from profile
├── replay_tool/
│   └── inject_typing.ahk    # AutoHotkey script for replaying
├── typing_sequence.txt      # Generated sequence ready for replay
└── README.md
```

## Requirements

- Python 3.6+
- AutoHotkey v1.1+ (for Windows)
- Python libraries:
  - tkinter
  - keyboard
  - numpy

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/biometric-typing-emulator.git
cd biometric-typing-emulator
```

2. Install required Python packages:
```
pip install keyboard numpy
```

3. Install AutoHotkey:
   - Windows: Download and install from [autohotkey.com](https://www.autohotkey.com/)

## Usage

### Starting the Application

Run the main GUI interface:

```
python biometric_typing_emulator/gui/interface.py
```

### Recording a Profile

1. Go to the "Record" tab
2. Select an existing profile or create a new one
3. Click "Start Recording"
4. Type naturally in the text area or in any application window
5. Click "Stop Recording" when finished
6. The typing data will be saved and the profile updated

### Generating and Replaying

1. Go to the "Generate & Replay" tab
2. Select a profile
3. Enter the text you want to type
4. Set options (pauses, corrections, etc.)
5. Click "Generate Sequence" to create a typing_sequence.txt file
6. Click "Generate & Replay" to create and immediately replay the sequence

### Profile Analysis

1. Go to the "Profile Analysis" tab
2. Select a profile
3. Click "Load Profile" to view statistics
4. Export/Import profiles as needed

## How It Works

### Recording

The recorder captures:
- Key press and release times
- Dwell time (how long a key is held)
- Flight time (gap between releasing one key and pressing the next)
- Correction information (backspaces, etc.)

### Profile Building

For each key and key-pair transition:
- Calculates weighted averages
- Updates standard deviations
- Stores in a JSON profile

### Sequence Generation

Based on a profile and input text:
- Generates realistic dwell and flight times using mean±random(0,stddev)
- Adds natural pauses at punctuation
- Optionally adds realistic mistakes and corrections

### Replay

The AutoHotkey script:
- Reads the sequence file
- Sends keyboard events at the OS level
- Controls precise timing for keydown and keyup events
- Creates a fully realistic typing simulation

## Testing Your Results

Test the emulator against typing biometric systems like:
- [TypingDNA Demo](https://demo.typingdna.com/)
- [KeyTrac](https://www.keytrac.net/en/demo)
- BehavioSec and similar services

## Disclaimer

This software is provided for educational and research purposes only. The authors do not condone or support any malicious use of this technology to bypass security systems or impersonate others. Users are responsible for ensuring their usage complies with applicable laws and regulations.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 