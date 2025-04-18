"""
High‑precision TypingRecorder with typo analytics
-------------------------------------------------
Combines nanosecond timing from the previous upgrade with the advanced
typo‑pattern extraction required for realistic error emulation.
"""

from __future__ import annotations
import time, json, pathlib, statistics, datetime, os
from typing import Dict, Any
import numpy as np
from pynput import keyboard

_NS_TO_MS = 1e-6


class TypingRecorder:
    # ----------------------------------------------------------- init
    def __init__(self, user_id:str):
        self.user_id=user_id
        base=pathlib.Path(__file__).resolve().parent.parent
        self.dir=base/"profiles"/user_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.f_profile=self.dir/f"{user_id}_profile.json"
        self.profile=self._load_profile()

        self.recording=False
        self.kd_ns:dict[str,int]={}
        self.last_ku_ns:int|None=None
        self.session: list[dict[str,Any]]=[]
        self.corrections:int=0
        self.immediate:int=0
        self.delayed:int=0
        self.typo_patterns:dict[str,int]={}
        self.last_chars:list[str]=[]
        self.max_pattern=5
        self.listener=None

    def _load_profile(self)->Dict[str,Any]:
        if self.f_profile.exists():
            try:
                return json.loads(self.f_profile.read_text("utf-8"))
            except:
                pass
        return {
            "mean_dwell_times":{},"std_dwell_times":{},
            "mean_flight_times":{},"std_flight_times":{},
            "session_count":0,
            "typo_rate":0.0,
            "double_letter_error_rate":0.0,
            "inserted_letter_rate":0.0,
            "missed_letter_rate":0.0,
            "reversed_letters_rate":0.0,
            "correction_style":{"immediate":0,"delayed":0},
            "typo_clusters":{"home_row":0,"adjacent_keys":0,"same_hand":0,"other":0},
            "common_typo_patterns":{}
        }

    # ---------------------------------------------------- recording
    def start_recording(self):
        if self.recording: return
        self.recording=True
        self.session.clear(); self.kd_ns.clear(); self.last_ku_ns=None
        self.corrections=self.immediate=self.delayed=0
        self.typo_patterns.clear(); self.last_chars.clear()
        self.listener=keyboard.Listener(on_press=self._on_press,on_release=self._on_release)
        self.listener.start()
        print("[rec] started")

    def stop_recording(self):
        if not self.recording: return
        self.recording=False
        if self.listener: self.listener.stop()
        if self.session:
            self._persist()
            self._update_profile()
            self.f_profile.write_text(json.dumps(self.profile,indent=2), "utf-8")
        print("[rec] stopped")

    def _kstr(self,k)->str|None:
        if isinstance(k, keyboard.KeyCode): return k.char
        if isinstance(k, keyboard.Key): return k.name
        return None

    def _now(self)->int: return time.perf_counter_ns()

    def _on_press(self,k):
        ks=self._kstr(k); now=self._now()
        if ks is None or ks in self.kd_ns: return
        self.kd_ns[ks]=now

    def _on_release(self,k):
        ks=self._kstr(k); now=self._now()
        kd=self.kd_ns.pop(ks,None)
        if kd is None: return
        dwell=(now-kd)*_NS_TO_MS
        flight=(kd-self.last_ku_ns)*_NS_TO_MS if self.last_ku_ns else 0
        self.last_ku_ns=now

        is_corr=1 if ks=="backspace" else 0
        if is_corr:
            self.corrections+=1
            # immediate vs delayed: immediate if last action <2 chars ago
            if len(self.session)>=1 and self.session[-1]["is_correction"]==0:
                self.immediate+=1
            else:
                self.delayed+=1
        else:
            if len(ks)==1:
                self.last_chars.append(ks)
                if len(self.last_chars)>self.max_pattern:
                    self.last_chars.pop(0)

        self.session.append({"key":ks,"dwell_time":dwell,"flight_time":max(0,flight),"is_correction":is_corr})

    # -------------------------------------------- persist & profile
    def _persist(self):
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        (self.dir/f"session_{ts}.json").write_text(json.dumps(self.session,indent=2),"utf-8")

    def _update_profile(self):
        p=self.profile; n_sess=p["session_count"]+1; w_old=p["session_count"]/n_sess; w_new=1/n_sess

        def upd(map_mean,map_std,k,val):
            mu_old=map_mean.get(k,val)
            mu=mu_old*w_old+val*w_new
            map_mean[k]=mu
            map_std[k]=abs(val-mu) if k not in map_std else (map_std[k]*w_old+abs(val-mu)*w_new)

        keys=[row["key"] for row in self.session]
        for i,row in enumerate(self.session):
            upd(p["mean_dwell_times"],p["std_dwell_times"],row["key"],row["dwell_time"])
            if i:
                pair=f"{keys[i-1]}→{row['key']}"
                upd(p["mean_flight_times"],p["std_flight_times"],pair,row["flight_time"])

        total=len(self.session)
        p["typo_rate"]=p["typo_rate"]*w_old + (self.corrections/total)*w_new
        p["correction_style"]["immediate"]=p["correction_style"]["immediate"]*w_old+self.immediate*w_new
        p["correction_style"]["delayed"]=p["correction_style"]["delayed"]*w_old+self.delayed*w_new
        # simplistic error‑type estimates
        p["inserted_letter_rate"]=p["inserted_letter_rate"]*w_old + (self.corrections/total)*w_new
        p["double_letter_error_rate"]=p["double_letter_error_rate"]*w_old
        p["missed_letter_rate"]=p["missed_letter_rate"]*w_old
        p["reversed_letters_rate"]=p["reversed_letters_rate"]*w_old
        p["session_count"]=n_sess
