import re
from typing import *
import subprocess
import pathlib

RULES = {"none": "",
         "en-sbe": pathlib.Path("rules/en-sbe.txt").read_text("utf-8"),
         "en-ortho": pathlib.Path("rules/en-orth.txt").read_text("utf-8")}


class Phonemizer:
    def __init__(self, language="en-GB-x-rp", special_rules=""):
        self.language = language
        self.special_rules = special_rules

        self.cache = {}

    def apply_rules(self, word: str, _rules=None):
        if _rules is None:
            _rules = self.special_rules
        for line in _rules.splitlines():
            if not line: continue

            # the best import system :)
            if line.startswith("INCLUDE"):
                word = self.apply_rules(word, RULES[line.split()[-1]])
                continue

            pattern, repl = line.split()
            word = re.sub(pattern, repl, word)
        return word

    def get_pronunciations(self, spellings: List[str]):
        new_spellings = list(set(s for s in spellings if s not in self.cache.keys()))
        for spelling in new_spellings:
            assert spelling.strip() != ""

        if new_spellings:
            espeak_input = "\n\n".join(new_spellings)
            # i wonder will this work on Macs :H
            espeak_output = subprocess.run([r"C:\Program Files\eSpeak NG\espeak-ng",
                                            "-q", "-x", "--ipa", "-v", self.language],
                                           input=espeak_input.encode("utf-8"),
                                           capture_output=True).stdout.decode("utf-8")
            new_pronunciations = espeak_output.splitlines()[::2]

            # this was hard to get right, may break again
            assert len(new_spellings) == len(new_pronunciations)

            for spelling, pronunciation in zip(new_spellings, new_pronunciations):
                self.cache[spelling] = self.apply_rules(pronunciation)

        return [self.cache[s] for s in spellings]

    def get_pronunciation(self, spelling: str):
        return self.get_pronunciations([spelling])[0]

    def no_stress(self, pronunciation: str):
        return re.sub(r"[ˈˌ]", "", pronunciation)

    def process_text(self, text: str, stress=True):
        units = []

        # max words without punctuation, without leading/trailing whitespace
        # \n is treated as special to force a line break in html output
        split_text = re.split(r"(\n|[\w\-']+([ ]+[\w\-']+)*)", text)
        punctuations = split_text[0::3]
        segments = ["\n" if s == "\n" else s.split(" ") for s in split_text[1::3]]

        # we want to call espeak only once
        # this will cache everything that could be used
        possible_units = []
        for segment in segments:
            if segment == "\n":
                continue
            for length in range(1, 6):
                possible_units.extend(" ".join(segment[i:i + length]) for i in range(len(segment) - length + 1))
        self.get_pronunciations(possible_units)

        for punctuation, segment in zip(punctuations, segments):
            if punctuation:
                units.append(((punctuation,), punctuation))
            if segment == "\n":
                units.append("\n")
                continue

            # we want units to be as short as possible so that we know what words phonemes come from
            # we try to grow a unit until it doesn't matter if it is ended or not
            start = 0
            while start < len(segment):
                stop = start + 1

                def _unit_incomplete():
                    if_separated = (self.get_pronunciation(" ".join(segment[start:stop])) + " " +
                                    self.get_pronunciation(segment[stop]))
                    if_joined = self.get_pronunciation(" ".join(segment[start:stop + 1]))
                    return self.no_stress(if_separated) != self.no_stress(if_joined)

                while stop < len(segment) and _unit_incomplete():
                    stop += 1

                units.append((segment[start:stop], self.get_pronunciation(" ".join(segment[start:stop]))))
                if stop < len(segment):
                    units.append(((" ",), " "))
                start = stop

        if punctuations[-1]:
            units.append(((punctuations[-1],), punctuations[-1]))

        if not stress:
            units = ["\n" if u == "\n" else (u[0], self.no_stress(u[1])) for u in units]

        # better structure for templating
        paragraphs = [[]]
        for unit in units:
            if unit == "\n":
                paragraphs.append([])
                continue
            paragraphs[-1].append(unit)

        return paragraphs
