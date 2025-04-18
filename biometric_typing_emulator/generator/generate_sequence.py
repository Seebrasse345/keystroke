"""
TypingSequenceGenerator – full typo modelling
============================================
• Synthesises keystroke‑level timing *and* stochastic error patterns that
  mirror the specific user profile collected by `record_typing.py`.
• Injects typos according to:
    – overall typo_rate
    – distribution of error types (double‑letter / inserted / missed / reversed)
    – cluster likelihoods (home‑row, adjacent, same‑hand, other)
    – common two‑char patterns (profile.common_typo_patterns)
• Then automatically repairs them (immediate vs delayed) in line with
  profile.correction_style.
• Final post‑pass guarantees the produced logical text == input text.
"""

from __future__ import annotations
import os, json, random, numpy as np
from typing import List, Dict, Any

class TypingSequenceGenerator:
    # ----------------------------------------------------- init / profile
    def __init__(self, user_id: str):
        self.user_id = user_id
        base = os.path.dirname(os.path.dirname(__file__))
        self.profile_path = os.path.join(base, "profiles", user_id, f"{user_id}_profile.json")
        self._load_profile()

        # static keyboard map
        self.qwerty_rows = [
            "1234567890-=",
            "qwertyuiop[]\\",
            "asdfghjkl;'",
            "zxcvbnm,./"
        ]
        self.left_hand = "qwertasdfgzxcv"
        self.right_hand = "yuiophjklnm"

    def _load_profile(self):
        with open(self.profile_path, "r", encoding="utf-8") as fh:
            self.profile: Dict[str, Any] = json.load(fh)
        if not self.profile.get("mean_dwell_times"):  # rudimentary check
            raise ValueError("Incomplete profile – record more data.")

    # ----------------------------------------------------------- timings
    def _dwell(self, key: str) -> float:
        md = self.profile["mean_dwell_times"]; sd = self.profile["std_dwell_times"]
        if key in md:
            return max(8.0, np.random.normal(md[key], sd.get(key, md[key]*.1)))
        avg = sum(md.values())/len(md)
        return max(8.0, np.random.normal(avg, avg*.1))

    def _flight(self, prev: str, curr: str) -> float:
        mf = self.profile["mean_flight_times"]; sf = self.profile["std_flight_times"]
        pair = f"{prev}→{curr}"
        if pair in mf:
            return max(3.0, np.random.normal(mf[pair], sf.get(pair, mf[pair]*.15)))
        avg = sum(mf.values())/len(mf)
        return max(3.0, np.random.normal(avg, avg*.15))

    # ----------------------------------------------------------- helpers
    def _map_char(self, ch: str) -> str:
        return { " ": "space", "\n": "enter", "\t": "tab" }.get(ch, ch)

    def _adjacent_keys(self, key: str) -> list[str]:
        for r, row in enumerate(self.qwerty_rows):
            if key in row:
                c = row.index(key); adj=[]
                adj += [row[c-1]] if c>0 else []
                adj += [row[c+1]] if c<len(row)-1 else []
                if r>0:
                    up = self.qwerty_rows[r-1]
                    adj += [up[i] for i in range(max(0,c-1),min(len(up),c+2))]
                if r<len(self.qwerty_rows)-1:
                    down = self.qwerty_rows[r+1]
                    adj += [down[i] for i in range(max(0,c-1),min(len(down),c+2))]
                return adj
        return list("qwertyuiopasdfghjklzxcvbnm")

    # ------------------------------------------------ typo generation
    def _should_typo(self) -> bool:
        return random.random() < self.profile.get("typo_rate", 0.03)

    def _choose_error_type(self) -> str:
        dist = {
            "double": self.profile.get("double_letter_error_rate", .4),
            "inserted": self.profile.get("inserted_letter_rate", .3),
            "missed": self.profile.get("missed_letter_rate", .2),
            "reversed": self.profile.get("reversed_letters_rate", .1)
        }
        tot = sum(dist.values())
        return random.choices(list(dist), weights=[v/tot for v in dist.values()])[0]

    def _choose_cluster(self) -> str:
        typ = self.profile.get("typo_clusters", {})
        dist = {k: typ.get(k,1) for k in ["home_row","adjacent_keys","same_hand","other"]}
        tot=sum(dist.values())
        if tot==0:
            return random.choice(list(dist))
        return random.choices(list(dist), weights=[v/tot for v in dist.values()])[0]

    def _error_key(self, correct: str, cluster: str, error_type:str) -> str:
        if error_type=="double": return correct
        if cluster=="home_row": pool="asdfghjkl;"  # simplistic
        elif cluster=="adjacent_keys": pool=self._adjacent_keys(correct)
        elif cluster=="same_hand":
            pool=self.left_hand if correct in self.left_hand else self.right_hand
        else:
            pool="qwertyuiopasdfghjklzxcvbnm"
        return random.choice(pool)

    # -------------- public --------------------------------------------
    def generate_sequence(self, text:str, *, add_errors:bool=True) -> List[Dict[str,Any]]:
        seq=[]
        prev=None
        logical_pos=0  # pointer into intended text

        while logical_pos < len(text):
            ch=text[logical_pos]
            key=self._map_char(ch)

            if add_errors and self._should_typo():
                typ=self._choose_error_type()
                cluster=self._choose_cluster()

                if typ=="double":
                    # press key twice then immediate backspace
                    seq.extend(self._emit_key(key, prev))
                    prev=key
                    seq.extend(self._emit_key(key, prev))
                    prev=key
                    seq.extend(self._emit_backspace(prev))
                    prev="backspace"

                elif typ=="inserted":
                    wrong=self._error_key(key,cluster,typ)
                    seq.extend(self._emit_key(wrong, prev))
                    prev=wrong
                    # delayed or immediate?
                    if random.random() < self._immediate_correction_prob():
                        seq.extend(self._emit_backspace(prev)); prev="backspace"
                    else:
                        # delay by 1-2 correct chars then backspace them all
                        lookahead=min(2,len(text)-logical_pos)
                        for i in range(lookahead):
                            nxt=self._map_char(text[logical_pos+i])
                            seq.extend(self._emit_key(nxt, prev)); prev=nxt
                        for _ in range(lookahead+1):
                            seq.extend(self._emit_backspace(prev)); prev="backspace"

                elif typ=="missed":
                    # skip char, type next, then backspace and retype
                    if logical_pos+1 < len(text):
                        nxt=self._map_char(text[logical_pos+1])
                        seq.extend(self._emit_key(nxt, prev)); prev=nxt
                        seq.extend(self._emit_backspace(prev)); prev="backspace"
                        seq.extend(self._emit_key(key, prev)); prev=key
                        logical_pos+=1  # we already processed next char
                elif typ=="reversed" and logical_pos+1 < len(text):
                    nxt=self._map_char(text[logical_pos+1])
                    seq.extend(self._emit_key(nxt, prev)); prev=nxt
                    seq.extend(self._emit_key(key, prev)); prev=key
                    # fix with two backspaces and correct order
                    seq.extend(self._emit_backspace(prev)); prev="backspace"
                    seq.extend(self._emit_backspace(prev)); prev="backspace"
                    seq.extend(self._emit_key(key, prev)); prev=key
                    seq.extend(self._emit_key(nxt, prev)); prev=nxt
                    logical_pos+=1
            # normal path
            seq.extend(self._emit_key(key, prev)); prev=key
            logical_pos+=1

        # final validation & repair
        if self._replay(seq) != text:
            seq=self._repair(seq,text)
        return seq

    # ------------------------------------------------------ emit helpers
    def _emit_key(self, key:str, prev:str|None)->List[Dict[str,Any]]:
        arr=[]
        # handle shift for upper-case
        if len(key)==1 and key.isupper():
            arr.extend(self._emit_key("shift", prev))
            prev="shift"
            key=key.lower()
            arr.append(self._make_event(key,prev)); prev=key
            arr.append(self._make_event("shift","shift"))  # Shift up acts like a key
        else:
            arr.append(self._make_event(key,prev))
        return arr

    def _emit_backspace(self, prev:str|None)->List[Dict[str,Any]]:
        return [self._make_event("backspace", prev, correction=1)]

    def _make_event(self,key:str, prev:str|None, correction:int=0)->Dict[str,Any]:
        return {
            "key":key,
            "dwell": self._dwell(key),
            "flight": 0 if prev is None else self._flight(prev,key),
            "is_correction": correction
        }

    def _immediate_correction_prob(self)->float:
        style=self.profile.get("correction_style",{"immediate":1,"delayed":1})
        tot=style["immediate"]+style["delayed"]
        if tot==0:
            return 0.5
        return style["immediate"]/tot if tot else .8

    def _replay(self,seq)->str:
        buf=[]
        for e in seq:
            k=e["key"]
            if k=="backspace":
                if buf: buf.pop()
            elif k in ("shift","ctrl","alt"): pass
            elif k in ("enter",):
                buf.append("\n")
            elif k in ("space"," "):
                buf.append(" ")
            elif len(k)==1:
                buf.append(k)
        return "".join(buf)

    def _repair(self,seq,text)->List[Dict[str,Any]]:
        current=self._replay(seq)
        # brute: bring to equality by backspacing diff tail & retyping
        # find divergence
        common=0
        for a,b in zip(current,text):
            if a==b: common+=1
            else: break
        surplus=len(current)-common
        prev=seq[-1]["key"]
        for _ in range(surplus):
            seq.append(self._make_event("backspace",prev,1)); prev="backspace"
        for ch in text[common:]:
            k=self._map_char(ch)
            seq.append(self._make_event(k,prev)); prev=k
        assert self._replay(seq)==text
        return seq

def save_sequence(sequence, output_path: str | None = None):
    """
    Persist sequence to a simple key|dwell|flight text file that the
    AHK replay tool consumes.
    """
    if output_path is None:
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_sequence.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("key|dwell|flight\n")
        for row in sequence:
            key = row["key"]
            # Map to AHK send syntax
            if key in ("space", " "):
                key_out = "{Space}"
            elif key == "enter":
                key_out = "{Enter}"
            elif key == "backspace":
                key_out = "{Backspace}"
            elif key == "tab":
                key_out = "{Tab}"
            elif len(key) == 1 and key in "+^!#{}":
                key_out = "{" + key + "}"
            else:
                key_out = key
            f.write(f"{key_out}|{int(row['dwell'])}|{int(row['flight'])}\n")
    return output_path