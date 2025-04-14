#Requires AutoHotkey v2.0+
#SingleInstance ; Default is Force in v2

; Set working directory to the script's directory
try SetWorkingDir(A_ScriptDir)
catch OSError as e
    MsgBox("Error setting working directory: " e.Message)

SendMode("Input")
try SetKeyDelay(-1, -1) ; Might need adjustment or different approach in v2 if problematic

; Set these to true to enable special modes
SIMULATE_KEYSTROKES := true   ; Set to false to just measure execution without typing
WAIT_FOR_FOCUS := true        ; Set to true to wait 3 seconds after launch before typing

; Path to the typing sequence file (relative to script or absolute)
sequenceFile := "..\typing_sequence.txt"

; Check if a custom sequence file was provided as a command line argument
if A_Args.Length > 0 {
    sequenceFile := A_Args[1]
}

; Load and validate the sequence file
if (!FileExist(sequenceFile)) {
    MsgBox("Error: Could not find typing sequence file.`nChecked: " (A_Args.Length > 0 ? A_Args[1] : "(Default)") "`nAnd: " A_ScriptDir . "\\..\\typing_sequence.txt")
    ExitApp()
}

; Normalize the path
if (!FileExist(sequenceFile)) {
    ; Try parent directory
    sequenceFile := "..\typing_sequence.txt"
    if (!FileExist(sequenceFile)) {
        ; Try project root
        sequenceFile := "..\..\typing_sequence.txt"
        if (!FileExist(sequenceFile)) {
            MsgBox("Error: Could not find typing sequence file")
            ExitApp()
        }
    }
}

; Wait for user to focus the desired application
if (WAIT_FOR_FOCUS) {
    MsgBox("Click OK and focus the window where you want to type within 3 seconds...", "Ready to type", "4096")
    Sleep(3000)
}

; Read and parse the typing sequence file
fileContent := ""
try {
    fileContent := FileRead(sequenceFile, "UTF-8") ; Specify UTF-8 encoding
}
catch OSError as e
{
    MsgBox("Error: Failed to read typing sequence file: " sequenceFile "`nOS Error: " e.Message)
    ExitApp()
}

; Parse the sequence
lines := StrSplit(fileContent, "`n", "`r")
header := lines[1]  ; First line is the header (key|dwell|flight)

; Validate header
if (Trim(header) != "key|dwell|flight") {
    MsgBox("Error: Invalid typing sequence file format.`nExpected header: key|dwell|flight`nFound: " header)
    ExitApp()
}

; Create sequence array
sequence := []
for i, line in lines {
    if (i = 1 || Trim(line) = "") ; Skip header and empty lines
        continue
        
    fields := StrSplit(line, "|")
    if (fields.Length < 3) {
        MsgBox("Warning: Skipping invalid line " i ": " line)
        continue
    }
        
    key := Trim(fields[1])
    dwell := Trim(fields[2])
    flight := Trim(fields[3])
    
    ; Basic validation for dwell/flight
    if !(IsInteger(dwell) && dwell >= 0 && IsInteger(flight) && flight >= 0) {
        MsgBox("Warning: Invalid dwell/flight time on line " i ": " line ". Skipping.")
        continue
    }
    
    sequence.Push(Map("key", key, "dwell", Integer(dwell), "flight", Integer(flight)))
}

; Check if sequence is empty after parsing
if sequence.Length < 1 {
    MsgBox("Error: No valid typing sequences found in file after parsing.")
    ExitApp()
}

; Display info about the sequence
totalKeys := sequence.Length
MsgBox("About to type " totalKeys " keystrokes. Press OK to begin...", "Ready to inject", "4096")

; Execute the typing sequence
keyCount := 0
startTime := A_TickCount

for i, keystroke in sequence {
    key := keystroke["key"]
    dwell := keystroke["dwell"]
    flight := keystroke["flight"]
    
    ; Wait for previous flight time
    if (flight > 0)
        Sleep(flight)
    
    ; Don't actually type if simulate mode is disabled (for testing)
    if (SIMULATE_KEYSTROKES) {
        ; Determine the raw key name for Send command
        rawKeyName := ""
        if (StrLen(key) > 1 && SubStr(key, 1, 1) = "{" && SubStr(key, StrLen(key)) = "}") { ; Check if it's {KeyName} format
             rawKeyName := SubStr(key, 2, StrLen(key) - 2) ; Extract content within {}
        } else if (StrLen(key) = 1) {
             rawKeyName := key ; Use the single character directly
        } else {
             MsgBox("Warning: Unrecognized key format on line " i+1 ": '" key "'. Skipping.")
             continue
        }

        ; Send the key down/up events using the correct syntax
        try {
            Send("{" rawKeyName " Down}")
            Sleep(dwell)
            Send("{" rawKeyName " Up}")
        } catch Error as e {
             ; Use rawKeyName in the error message
             MsgBox("Error sending key '" rawKeyName "': " e.Message ". Aborting.", "Send Error")
             ExitApp()
        }
    } else {
        ; Just simulate the timing without typing
        Sleep(dwell)
    }
    
    keyCount += 1
    
    ; Show progress every 10 keystrokes
    if (Mod(keyCount, 10) = 0) {
        progress := Floor((keyCount / totalKeys) * 100)
        ToolTip("Typing: " progress "% complete (" keyCount "/" totalKeys ")")
    }
}

; Display completion message
endTime := A_TickCount
totalTime := (endTime - startTime) / 1000
avgKeystrokeTime := (keyCount > 0) ? (totalTime / keyCount) * 1000 : 0 ; Avoid division by zero

ToolTip()  ; Clear tooltip
MsgBox("Successfully typed " keyCount " keystrokes in " Format("{:.2f}", totalTime) " seconds.`nAverage time per keystroke: " Format("{:.2f}", avgKeystrokeTime) " ms", "Typing Complete", "0")

ExitApp()

; Add a hotkey to abort typing
^Escape:: {
    MsgBox("Typing sequence aborted by user.", "Aborted", "0")
    ExitApp()
} 