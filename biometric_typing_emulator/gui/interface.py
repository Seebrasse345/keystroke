"""
Biometric Typing Emulator – complete upgraded GUI
=================================================
• End‑to‑end interface for recording, analysing, generating and replaying
  keystroke sequences that mimic a user's biometric typing profile,
  including realistic typo patterns.
• Works with the enhanced `TypingRecorder`, `TypingSequenceGenerator`,
  and updated AutoHotkey replay script.
"""

from __future__ import annotations
import os, sys, json, subprocess, tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from threading import Thread

# allow project‑root imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from recorder.record_typing import TypingRecorder
from generator.generate_sequence import TypingSequenceGenerator


class BiometricGUI(tk.Tk):
    # ------------------------------------------------------------------
    # init
    # ------------------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.title("Biometric Typing Emulator")
        self.geometry("900x650")
        self.minsize(600, 520)

        self._build_styles()
        self._setup_vars()
        self._build_tabs()
        self._load_settings()

    # ------------------------------------------------------------------
    # internal state vars
    # ------------------------------------------------------------------
    def _setup_vars(self):
        self.users = self._get_profiles()
        self.user_var = tk.StringVar(value=self.users[0] if self.users else "")
        self.profile_var = tk.StringVar(value=self.users[0] if self.users else "")
        self.default_user_var = tk.StringVar()
        self.use_typos_var = tk.BooleanVar(value=True)
        self.ahk_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.record_status_var = tk.StringVar(value="Ready")
        self.ahk_status_var = tk.StringVar(value="Unknown")
        self.new_user_var = tk.StringVar()

        self.recorder: TypingRecorder | None = None

    # ------------------------------------------------------------------
    # styles
    # ------------------------------------------------------------------
    def _build_styles(self):
        self.style = ttk.Style(self)
        self.style.configure("TFrame", background="#f4f4f4")
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), background="#f4f4f4")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 11), background="#f4f4f4")
        self.style.configure("Generate.TButton", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    # tabs
    # ------------------------------------------------------------------
    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.main_tab = ttk.Frame(self.notebook)
        self.record_tab = ttk.Frame(self.notebook)
        self.profile_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.main_tab, text="Generate && Replay")
        self.notebook.add(self.record_tab, text="Record")
        self.notebook.add(self.profile_tab, text="Profile")
        self.notebook.add(self.settings_tab, text="Settings")

        self._init_main_tab()
        self._init_record_tab()
        self._init_profile_tab()
        self._init_settings_tab()

    # ------------------------------------------------------------------ MAIN TAB
    def _init_main_tab(self):
        frame = ttk.Frame(self.main_tab, padding=10); frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Generate & Replay Typing Sequence", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))

        # profile select
        pf = ttk.Frame(frame); pf.pack(fill=tk.X, pady=3)
        ttk.Label(pf, text="Profile:").pack(side=tk.LEFT, padx=(0,5))
        self.user_combo = ttk.Combobox(pf, textvariable=self.user_var, values=self.users, state="readonly", width=18)
        self.user_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(pf, text="Refresh", command=self._refresh_users).pack(side=tk.LEFT, padx=5)

        # text input
        ttk.Label(frame, text="Text to type:", style="SubHeader.TLabel").pack(anchor=tk.W, pady=(15,4))
        self.text_input = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=8)
        self.text_input.pack(fill=tk.BOTH, expand=True, pady=4)

        # options
        opts = ttk.LabelFrame(frame, text="Generation Options"); opts.pack(fill=tk.X, pady=10, ipady=2)
        ttk.Checkbutton(opts, text="Use my real typo pattern", variable=self.use_typos_var).pack(anchor=tk.W, padx=10, pady=5)

        # buttons
        bf = ttk.Frame(frame); bf.pack(fill=tk.X, pady=12)
        ttk.Button(bf, text="Generate Sequence", style="Generate.TButton", command=self._generate_sequence_ui).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Generate & Replay", style="Generate.TButton", command=self._generate_replay_ui).pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM, pady=(8,0))

    # ------------------------------------------------------------------ RECORD TAB
    def _init_record_tab(self):
        frame = ttk.Frame(self.record_tab, padding=10); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Record Typing Biometrics", style="Header.TLabel").pack(anchor=tk.W, pady=(0,10))

        # profile select / create
        pf = ttk.Frame(frame); pf.pack(fill=tk.X, pady=3)
        ttk.Label(pf, text="Profile:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Combobox(pf, textvariable=self.user_var, values=self.users, width=18).pack(side=tk.LEFT, padx=5)

        ttk.Label(pf, text="New:").pack(side=tk.LEFT, padx=(12,5))
        ttk.Entry(pf, textvariable=self.new_user_var, width=15).pack(side=tk.LEFT)
        ttk.Button(pf, text="Create", command=self._create_user).pack(side=tk.LEFT, padx=5)

        # record text area
        ttk.Label(frame, text="Type or paste text here while recording:",
                  style="SubHeader.TLabel").pack(anchor=tk.W, pady=(12,4))
        self.record_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=6, state=tk.DISABLED)
        self.record_text.pack(fill=tk.BOTH, expand=True, pady=4)

        bf = ttk.Frame(frame); bf.pack(fill=tk.X, pady=10)
        self.start_btn = ttk.Button(bf, text="Start Recording", command=self._start_recording)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(bf, text="Stop", state=tk.DISABLED, command=self._stop_recording)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, textvariable=self.record_status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM, pady=(8,0))

    # ------------------------------------------------------------------ PROFILE TAB
    def _init_profile_tab(self):
        frame = ttk.Frame(self.profile_tab, padding=10); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Profile Analysis", style="Header.TLabel").pack(anchor=tk.W, pady=(0,10))

        pf = ttk.Frame(frame); pf.pack(fill=tk.X, pady=3)
        ttk.Label(pf, text="Profile:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Combobox(pf, textvariable=self.profile_var, values=self.users, state="readonly", width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(pf, text="Refresh", command=self._refresh_users).pack(side=tk.LEFT, padx=5)
        ttk.Button(pf, text="Load", command=self._load_profile_ui).pack(side=tk.LEFT, padx=5)

        self.profile_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=14)
        self.profile_text.pack(fill=tk.BOTH, expand=True, pady=6)

        af = ttk.Frame(frame); af.pack(fill=tk.X, pady=6)
        ttk.Button(af, text="Export", command=self._export_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(af, text="Import", command=self._import_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(af, text="Delete", command=self._delete_profile).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------ SETTINGS TAB
    def _init_settings_tab(self):
        frame = ttk.Frame(self.settings_tab, padding=10); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Settings", style="Header.TLabel").pack(anchor=tk.W, pady=(0,10))

        ahk_row = ttk.Frame(frame); ahk_row.pack(fill=tk.X, pady=4)
        ttk.Label(ahk_row, text="AutoHotkey path:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(ahk_row, textvariable=self.ahk_path_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(ahk_row, text="Browse", command=self._browse_ahk).pack(side=tk.LEFT, padx=5)

        df = ttk.LabelFrame(frame, text="Defaults"); df.pack(fill=tk.X, pady=8)
        uf = ttk.Frame(df); uf.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(uf, text="Default profile:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Combobox(uf, textvariable=self.default_user_var, values=self.users, width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="Save Settings", command=self._save_settings).pack(pady=10)

        chk = ttk.Frame(frame); chk.pack(fill=tk.X, pady=6)
        ttk.Button(chk, text="Check AHK", command=self._check_ahk).pack(side=tk.LEFT, padx=5)
        ttk.Label(chk, textvariable=self.ahk_status_var).pack(side=tk.LEFT, padx=8)

    # ======================== back‑end helpers =========================
    def _profiles_dir(self):
        return os.path.join(PROJECT_ROOT, "profiles")

    def _get_profiles(self):
        d = self._profiles_dir()
        if not os.path.exists(d): os.makedirs(d)
        return [p for p in os.listdir(d) if os.path.isdir(os.path.join(d,p))]

    def _refresh_users(self):
        self.users = self._get_profiles()
        self.user_combo["values"] = self.users
        self.default_user_var.set(self.default_user_var.get() if self.default_user_var.get() in self.users else "")
        self.profile_var.set(self.profile_var.get() if self.profile_var.get() in self.users else (self.users[0] if self.users else ""))

    # ----------------------------- recording
    def _start_recording(self):
        uid=self.user_var.get()
        if not uid:
            messagebox.showerror("Error","Select profile first");return
        self.recorder=TypingRecorder(uid); self.recorder.start_recording()
        self.record_text.config(state=tk.NORMAL); self.record_text.delete("1.0",tk.END)
        self.start_btn.config(state=tk.DISABLED); self.stop_btn.config(state=tk.NORMAL)
        self.record_status_var.set(f"Recording for '{uid}'…")

    def _stop_recording(self):
        if self.recorder: self.recorder.stop_recording()
        self.record_text.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL); self.stop_btn.config(state=tk.DISABLED)
        self.record_status_var.set("Recording stopped.")
        self._refresh_users()

    # ----------------------------- generation helpers
    def _generate_sequence(self, uid:str, text:str):
        gen=TypingSequenceGenerator(uid)
        return gen.generate_sequence(text, add_errors=self.use_typos_var.get())

    # UI wrappers
    def _generate_sequence_ui(self):
        uid = self.user_var.get()
        txt = self.text_input.get("1.0", tk.END).rstrip("\n")
        if not uid or not txt:
            messagebox.showerror("Error", "Select profile and enter text"); return
        try:
            self.status_var.set("Generating…"); self.update()
            seq = self._generate_sequence(uid, txt)
            out = TypingSequenceGenerator(uid).save_sequence(seq)
            self.status_var.set(f"Saved to {out}")
            messagebox.showinfo("Success", f"Sequence saved to:\n{out}")
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error")
        finally:
            self.after(1000, lambda: self.status_var.set("Ready"))

    def _generate_replay_ui(self):
        uid = self.user_var.get()
        txt = self.text_input.get("1.0", tk.END).rstrip("\n")
        if not uid or not txt:
            messagebox.showerror("Error", "Select profile and enter text"); return
        if not self._valid_ahk():
            messagebox.showerror("Error", "Configure AutoHotkey path"); return
        try:
            self.status_var.set("Generating…"); self.update()
            seq = self._generate_sequence(uid, txt)
            out = TypingSequenceGenerator(uid).save_sequence(seq)
            self.status_var.set("Replaying…")
            Thread(target=self._run_ahk, args=(out,), daemon=True).start()
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Error", str(e)); self.status_var.set("Ready")

    # ----------------------------- AHK
    def _valid_ahk(self): return os.path.isfile(self.ahk_path_var.get()) and self.ahk_path_var.get().lower().endswith(".exe")
    def _browse_ahk(self):
        p=filedialog.askopenfilename(filetypes=[("Executable","*.exe")]); 
        if p: self.ahk_path_var.set(p)

    def _run_ahk(self, sequence_path:str):
        script=os.path.join(PROJECT_ROOT,"replay_tool","inject_typing.ahk")
        try:
            subprocess.run([self.ahk_path_var.get(), script, sequence_path], check=True)
            self.after(0, lambda: self.status_var.set("Replay done"))
        except Exception as e:
            import traceback; traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("AHK error",str(e)))
            self.after(0, lambda: self.status_var.set("Error"))

    # ----------------------------- profile tab actions
    def _load_profile_ui(self):
        pid=self.profile_var.get()
        if not pid: return
        f=os.path.join(self._profiles_dir(),pid,f"{pid}_profile.json")
        if not os.path.isfile(f):
            messagebox.showerror("Error","Profile file not found"); return
        data=json.load(open(f,"r",encoding="utf-8"))
        self.profile_text.delete("1.0",tk.END)
        self.profile_text.insert(tk.END,json.dumps(data,indent=2))

    def _create_user(self):
        name=self.new_user_var.get().strip()
        if not name: messagebox.showerror("Error","Enter name"); return
        d=os.path.join(self._profiles_dir(),name)
        if os.path.exists(d):
            messagebox.showerror("Error","Profile exists"); return
        os.makedirs(d, exist_ok=True)
        self._refresh_users(); self.user_var.set(name); self.profile_var.set(name)
        messagebox.showinfo("Created",f"Profile '{name}' created")

    def _export_profile(self):
        pid=self.profile_var.get()
        if not pid: return
        src=os.path.join(self._profiles_dir(),pid,f"{pid}_profile.json")
        if not os.path.exists(src):
            messagebox.showerror("Error","Profile not found"); return
        dst=filedialog.asksaveasfilename(defaultextension=".json",initialfile=f"{pid}_profile.json")
        if not dst: return
        with open(src,"r") as s, open(dst,"w") as d: d.write(s.read())
        messagebox.showinfo("Exported",dst)

    def _import_profile(self):
        path=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            data=json.load(open(path,"r"))
            if not {"mean_dwell_times","mean_flight_times","session_count"}<=data.keys():
                raise ValueError("Invalid profile file")
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Error",f"Failed: {e}"); return
        name=os.path.basename(path).split("_profile.json")[0]+"_import"
        d=os.path.join(self._profiles_dir(),name); os.makedirs(d, exist_ok=True)
        dst=os.path.join(d,f"{name}_profile.json")
        json.dump(data,open(dst,"w"),indent=2)
        self._refresh_users(); messagebox.showinfo("Imported",name)

    def _delete_profile(self):
        pid=self.profile_var.get()
        if not pid: return
        if not messagebox.askyesno("Confirm",f"Delete profile '{pid}'?"): return
        import shutil
        shutil.rmtree(os.path.join(self._profiles_dir(),pid), ignore_errors=True)
        self._refresh_users()

    # ----------------------------- settings persistence
    def _settings_file(self):
        return os.path.join(PROJECT_ROOT,"settings.json")

    def _load_settings(self):
        if not os.path.isfile(self._settings_file()): return
        try:
            s=json.load(open(self._settings_file(),"r"))
            self.ahk_path_var.set(s.get("ahk_path",""))
            self.default_user_var.set(s.get("default_user",""))
            if self.default_user_var.get() in self.users:
                self.user_var.set(self.default_user_var.get())
        except Exception as e:
            import traceback; traceback.print_exc()
            print("Settings load error:",e)

    def _save_settings(self):
        json.dump({"ahk_path":self.ahk_path_var.get(),"default_user":self.default_user_var.get()},
                  open(self._settings_file(),"w"), indent=2)
        messagebox.showinfo("Saved","Settings saved")

    def _check_ahk(self):
        if not self._valid_ahk():
            self.ahk_status_var.set("Invalid")
            return
        try:
            res=subprocess.run([self.ahk_path_var.get(),"/version"],capture_output=True,text=True,check=False)
            self.ahk_status_var.set("Installed: "+(res.stdout.strip() or "Unknown"))
        except Exception as e:
            import traceback; traceback.print_exc()
            self.ahk_status_var.set(f"Error: {e}")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    BiometricGUI().mainloop()
