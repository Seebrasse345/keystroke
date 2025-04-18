"""
TypingSequenceGenerator – final fixed build
===========================================
• Uses per‑user timing & typo stats.
• Shift treated as press+release: only the *next* character is upper‑cased,
  so replay validation always matches the intended text.
• Guards against zero‑weight distributions.
• Provides save_sequence() for GUI / AHK replay.
"""

from __future__ import annotations
import os, json, random, numpy as np
from typing import List, Dict, Any


class TypingSequenceGenerator:
    # ------------------------------------------------------------------ init
    def __init__(self, user_id: str):
        root = os.path.dirname(os.path.dirname(__file__))
        self.user_id = user_id
        self.profile_path = os.path.join(root, "profiles", user_id,
                                         f"{user_id}_profile.json")
        with open(self.profile_path, "r", encoding="utf-8") as f:
            self.profile = json.load(f)

        if not self.profile.get("mean_dwell_times"):
            raise ValueError("Profile incomplete – record more data.")

        # simple keyboard map
        self.rows = [
            "1234567890-=",
            "qwertyuiop[]\\",
            "asdfghjkl;'",
            "zxcvbnm,./"
        ]
        self.left = "qwertasdfgzxcv"
        self.right = "yuiophjklnm"

    # ----------------------------------------------------- low‑level timing
    def _dwell(self, key: str):
        md, sd = self.profile["mean_dwell_times"], self.profile["std_dwell_times"]
        if key in md:
            return max(8.0, np.random.normal(md[key], sd.get(key, md[key] * .1)))
        mean = sum(md.values()) / len(md)
        return max(8.0, np.random.normal(mean, mean * .1))

    def _flight(self, prev: str, curr: str):
        mf, sf = self.profile["mean_flight_times"], self.profile["std_flight_times"]
        pair = f"{prev}→{curr}"
        if pair in mf:
            return max(3.0, np.random.normal(mf[pair], sf.get(pair, mf[pair] * .15)))
        mean = sum(mf.values()) / len(mf)
        return max(3.0, np.random.normal(mean, mean * .15))

    # --------------------------------------------------------- typo helpers
    def _should_typo(self):     return random.random() < self.profile.get("typo_rate", .03)

    def _pick(self, d: dict):   # safe choice even if all weights zero
        tot = sum(d.values())
        if tot == 0: return random.choice(list(d))
        return random.choices(list(d), weights=[v / tot for v in d.values()])[0]

    def _error_type(self):
        return self._pick({
            "double":   self.profile.get("double_letter_error_rate", .4),
            "inserted": self.profile.get("inserted_letter_rate",      .3),
            "missed":   self.profile.get("missed_letter_rate",        .2),
            "reversed": self.profile.get("reversed_letters_rate",     .1)
        })

    def _cluster(self):
        typ = self.profile.get("typo_clusters", {})
        return self._pick({k: typ.get(k, 1) for k in
                           ["home_row", "adjacent_keys", "same_hand", "other"]})

    def _error_key(self, key: str, cluster: str):
        if cluster == "home_row":  pool = "asdfghjkl;"
        elif cluster == "adjacent_keys": pool = self._adjacent(key)
        elif cluster == "same_hand": pool = self.left if key in self.left else self.right
        else: pool = "qwertyuiopasdfghjklzxcvbnm"
        return random.choice(pool)

    def _adjacent(self, key: str):
        for r, row in enumerate(self.rows):
            if key in row:
                c = row.index(key); adj = []
                if c > 0: adj.append(row[c-1])
                if c < len(row)-1: adj.append(row[c+1])
                if r: adj += [self.rows[r-1][i]
                              for i in range(max(0, c-1), min(len(self.rows[r-1]), c+2))]
                if r < len(self.rows)-1:
                    adj += [self.rows[r+1][i]
                            for i in range(max(0, c-1), min(len(self.rows[r+1]), c+2))]
                return adj
        return list("qwertyuiopasdfghjklzxcvbnm")

    def _immediate_prob(self):
        st = self.profile.get("correction_style", {"immediate": 4, "delayed": 1})
        tot = st["immediate"] + st["delayed"]
        return .8 if tot == 0 else st["immediate"] / tot

    # --------------------------------------------------------- key emitter
    def _emit(self, key: str, prev: str | None, corr=0):
        return {
            "key": key,
            "dwell": self._dwell(key),
            "flight": 0 if prev is None else self._flight(prev, key),
            "is_correction": corr
        }

    def _emit_key(self, key: str, prev: str | None):
        res, p = [], prev
        if len(key) == 1 and key.isupper():
            res.append(self._emit("shift", p)); p = "shift"
            res.append(self._emit(key.lower(), p)); p = key.lower()
            res.append(self._emit("shift", p))      # release
        else:
            res.append(self._emit(key, p))
        return res, res[-1]["key"]

    def _emit_bs(self, prev: str):
        ev = self._emit("backspace", prev, corr=1)
        return [ev], ev["key"]

    # --------------------------------------------------- generation engine
    def generate_sequence(self, text: str, *, add_errors=True) -> List[Dict[str, Any]]:
        seq, prev = [], None
        i = 0
        while i < len(text):
            ch = text[i]
            key = {" ": "space", "\n": "enter", "\t": "tab"}.get(ch, ch)

            # optional typo injection
            if add_errors and self._should_typo():
                etype = self._error_type(); cl = self._cluster()
                if etype == "double":
                    ev, prev = self._emit_key(key, prev); seq += ev
                    ev, prev = self._emit_key(key, prev); seq += ev
                    ev, prev = self._emit_bs(prev);       seq += ev

                elif etype == "inserted":
                    wrong = self._error_key(key, cl)
                    ev, prev = self._emit_key(wrong, prev); seq += ev
                    if random.random() < self._immediate_prob():
                        ev, prev = self._emit_bs(prev); seq += ev
                    else:
                        look = min(2, len(text)-i)
                        for j in range(look):
                            nxt = {" ": "space", "\n": "enter", "\t": "tab"}.get(text[i+j], text[i+j])
                            ev, prev = self._emit_key(nxt, prev); seq += ev
                        for _ in range(look+1):
                            ev, prev = self._emit_bs(prev); seq += ev

                elif etype == "missed" and i+1 < len(text):
                    nxt = {" ": "space", "\n": "enter", "\t": "tab"}.get(text[i+1], text[i+1])
                    ev, prev = self._emit_key(nxt, prev); seq += ev
                    ev, prev = self._emit_bs(prev);       seq += ev
                    ev, prev = self._emit_key(key, prev); seq += ev
                    i += 1  # consumed an extra char

                elif etype == "reversed" and i+1 < len(text):
                    nxt = {" ": "space", "\n": "enter", "\t": "tab"}.get(text[i+1], text[i+1])
                    ev, prev = self._emit_key(nxt, prev); seq += ev
                    ev, prev = self._emit_key(key, prev); seq += ev
                    ev, prev = self._emit_bs(prev); seq += ev
                    ev, prev = self._emit_bs(prev); seq += ev
                    ev, prev = self._emit_key(key, prev); seq += ev
                    ev, prev = self._emit_key(nxt, prev); seq += ev
                    i += 1

            # intended character
            ev, prev = self._emit_key(key, prev); seq += ev
            i += 1

        # final validation & minimal repair
        if self._replay(seq) != text:
            seq = self._repair(seq, text)
        return seq

    # ----------------------------------------------------- replay / repair
    def _replay(self, seq) -> str:
        buf = []
        shift_armed = False
        expect_release = False
        for ev in seq:
            k = ev["key"]

            if k == "shift":
                if not expect_release:       # this is the press
                    shift_armed = True
                    expect_release = True
                else:                       # this is the release
                    expect_release = False
                continue

            if k == "backspace":
                if buf: buf.pop(); continue
            if k in ("ctrl", "alt"): continue
            if k == "enter": buf.append("\n"); continue
            if k in ("space", " "): buf.append(" "); continue

            if len(k) == 1:
                buf.append(k.upper() if shift_armed else k)
                shift_armed = False
        return "".join(buf)

    def _repair(self, seq, target: str):
        current = self._replay(seq)
        pos = 0
        while pos < min(len(current), len(target)) and current[pos] == target[pos]:
            pos += 1
        surplus = len(current) - pos
        prev = seq[-1]["key"]
        for _ in range(surplus):
            bs, prev = self._emit_bs(prev); seq += bs

        for ch in target[pos:]:
            key = {" ": "space", "\n": "enter", "\t": "tab"}.get(ch, ch)
            ev, prev = self._emit_key(key, prev); seq += ev

        assert self._replay(seq) == target
        return seq

    # ---------------------------------------------------------- saving
    def save_sequence(self, sequence: List[Dict[str, Any]],
                      out_path: str | None = None) -> str:
        if out_path is None:
            out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "typing_sequence.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("key|dwell|flight\n")
            for ev in sequence:
                f.write(f"{self._ahk_key(ev['key'])}|"
                        f"{int(ev['dwell'])}|{int(ev['flight'])}\n")
        return out_path

    @staticmethod
    def _ahk_key(k: str) -> str:
        if k in ("space", " "): return "{Space}"
        if k == "enter": return "{Enter}"
        if k == "backspace": return "{Backspace}"
        if k == "tab": return "{Tab}"
        if len(k) == 1 and k in "+^!#{}": return "{" + k + "}"
        return k
