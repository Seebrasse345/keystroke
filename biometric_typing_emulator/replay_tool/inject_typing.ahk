; Requires AutoHotkey v2
#SingleInstance Force
SetWorkingDir A_ScriptDir
SendMode "Input"
SetKeyDelay -1, -1

SIMULATE_KEYSTROKES := true
WAIT_FOR_FOCUS      := true

sequenceFile := "..\typing_sequence.txt"
if A_Args.Length >= 1
    sequenceFile := A_Args[1]

if !FileExist(sequenceFile) {
    MsgBox "Cannot find typing_sequence.txt - aborting"
    ExitApp
}

if WAIT_FOR_FOCUS {
    MsgBox "Click OK, then focus the target window within 3 s", "Typing Emulator", 4096
    Sleep 3000
}

lines := StrSplit(FileRead(sequenceFile, "UTF-8"), "`n", "`r")
if Trim(lines[1]) != "key|dwell|flight" {
    MsgBox "Invalid sequence file – bad header"
    ExitApp
}

sequence := []
Loop lines.Length - 1
{
    idx := A_Index + 1
    lineText  := Trim(lines[idx])
    if lineText = ""
        Continue
    fields := StrSplit(lineText, "|")
    if fields.Length < 3
        Continue
    sequence.Push Map(
        "key",    Trim(fields[1]),
        "dwell",  Integer(Trim(fields[2])),
        "flight", Integer(Trim(fields[3]))
    )
}

normaliseKey(name) {
    static specials := Map(
        "shift", "Shift",
        "ctrl",  "Ctrl",
        "alt",   "Alt",
        "enter", "Enter",
        "tab",   "Tab",
        "space", "Space",
        "backspace", "Backspace"
    )
    if specials.Has(Trim(name))
        return specials[Trim(name)]
    return name ; may already be {X}
}

MsgBox "Typing " sequence.Length " keystrokes …", "Emulator", 4096

prevKey := ""
For each, stroke in sequence
{
    if stroke["flight"] > 0
        Sleep stroke["flight"]

    if !SIMULATE_KEYSTROKES
    {
        Sleep stroke["dwell"]
        Continue
    }

    keyName := stroke["key"]

    if SubStr(keyName,1,1)="{" && SubStr(keyName,-1)="}"
        rawName := SubStr(keyName,2,StrLen(keyName)-2)
    else if StrLen(keyName)=1
        rawName := keyName
    else
        rawName := normaliseKey(keyName)

    try {
        Send("{" rawName " Down}")
        Sleep stroke["dwell"]
        Send("{" rawName " Up}")
    } catch as e {
        MsgBox "Send error on '" rawName "': " e.Message
        ExitApp
    }
}

MsgBox "Done!", "Emulator"
ExitApp
