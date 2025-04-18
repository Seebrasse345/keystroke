"""
TypingSequenceGenerator – simplified, uppercase‑safe
====================================================
• Generates per‑user keystroke sequences (dwell / flight / typos).
• Emits capital letters directly (e.g. "T"), so the replay script
  sends them correctly without explicit Shift events.
• Looks up timing stats with lowercase equivalents, so missing
  uppercase keys in the profile never cause problems.
• Keeps save_sequence() helper used by the GUI / AHK replay.
"""

from __future__ import annotations
import os, json, random, numpy as np
from typing import Dict, Any, List


class TypingSequenceGenerator:
    # --------------------------------------------------------------- init
    def __init__(self, user_id: str):
        root = os.path.dirname(os.path.dirname(__file__))
        self.user_id = user_id
        prof = os.path.join(root, "profiles", user_id,
                            f"{user_id}_profile.json")
        with open(prof, "r", encoding="utf-8") as fh:
            self.profile: Dict[str, Any] = json.load(fh)

        if not self.profile.get("mean_dwell_times"):
            raise ValueError("Profile incomplete – record more data.")

    # -------------------------------------------------- timing utilities
    def _dwell(self, key: str) -> float:
        k = key.lower() if len(key) == 1 else key
        md, sd = self.profile["mean_dwell_times"], self.profile["std_dwell_times"]
        if k in md:
            return max(8.0, np.random.normal(md[k], sd.get(k, md[k]*0.1)))
        mean = sum(md.values()) / len(md)
        return max(8.0, np.random.normal(mean, mean*0.1))

    def _flight(self, prev: str, curr: str) -> float:
        p, c = (prev.lower() if len(prev) == 1 else prev,
                curr.lower() if len(curr) == 1 else curr)
        pair = f"{p}→{c}"
        mf, sf = self.profile["mean_flight_times"], self.profile["std_flight_times"]
        if pair in mf:
            return max(3.0, np.random.normal(mf[pair], sf.get(pair, mf[pair]*0.15)))
        mean = sum(mf.values()) / len(mf)
        return max(3.0, np.random.normal(mean, mean*0.15))

    # ----------------------------------------------------- typo helpers
    def _should_typo(self) -> bool:
        return random.random() < self.profile.get("typo_rate", .03)

    def _pick(self, d: dict) -> str:
        tot = sum(d.values())
        if tot == 0:
            return random.choice(list(d))
        return random.choices(list(d), weights=[v/tot for v in d.values()])[0]

    def _error_type(self) -> str:
        return self._pick({
            "double":   self.profile.get("double_letter_error_rate", .4),
            "inserted": self.profile.get("inserted_letter_rate",      .3),
            "missed":   self.profile.get("missed_letter_rate",        .2),
            "reversed": self.profile.get("reversed_letters_rate",     .1)
        })

    def _immediate_prob(self) -> float:
        st = self.profile.get("correction_style", {"immediate": 4, "delayed": 1})
        tot = st["immediate"] + st["delayed"]
        return .8 if tot == 0 else st["immediate"] / tot

    # --------------------------------------------------- emit utilities
    def _emit(self, key: str, prev: str | None, corr: int = 0) -> Dict[str, Any]:
        return {
            "key": key,
            "dwell": self._dwell(key),
            "flight": 0 if prev is None else self._flight(prev, key),
            "is_correction": corr
        }

    def _emit_key(self, key: str, prev: str | None):
        ev = self._emit(key, prev)
        return [ev], ev["key"]

    def _emit_bs(self, prev: str):
        ev = self._emit("backspace", prev, corr=1)
        return [ev], ev["key"]

    # -------------------------------------------------- main generator
    def generate_sequence(self, text: str, *, add_errors=True) -> List[Dict[str, Any]]:
        seq, prev = [], None
        i = 0
        while i < len(text):
            ch = text[i]
            key = {" ": "space", "\n": "enter", "\t": "tab"}.get(ch, ch)

            # (Optional) very small typo demo – feel free to extend
            if add_errors and self._should_typo() and key.isalpha():
                ev, prev = self._emit_key(key, prev); seq += ev
                ev, prev = self._emit_key(key, prev); seq += ev  # duplicate
                ev, prev = self._emit_bs(prev); seq += ev        # delete
            else:
                ev, prev = self._emit_key(key, prev); seq += ev
            i += 1

        return seq  # No complex repair needed with direct uppercase emit

    # -------------------------------------------------------- saving
    def save_sequence(self, seq: List[Dict[str, Any]],
                      out_path: str | None = None) -> str:
        if out_path is None:
            out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "typing_sequence.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("key|dwell|flight\n")
            for ev in seq:
                fh.write(f"{self._ahk_key(ev['key'])}|"
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
