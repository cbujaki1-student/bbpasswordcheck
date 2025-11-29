#!/usr/bin/env python3
"""

Script to force a password change on the default "bbuser" account as
configured and deployed using cloud-init on the BeaglePlay device

Designed to be triggered by cloud-init on the first boot

Prompts user for a password and confirmation password, then sets the
default bbuser accound password to the user input password

Password must meet a set of configured requirements and cannot match
dictionary words as defined in the cracklib file native to Armbian

"""

import sys
import re
import subprocess
import getpass
import os
from pathlib import Path

# Configurable password settings
MARKER = Path(f"/home/bbuser/.bb_password_done")
MIN_LENGTH = 12
MIN_DICT_WORD_LEN = 4
MAX_LEET_SUBSTITUTION = 2

DEFAULT_DICT_FILES = [
    "/usr/share/dict/cracklib-small",
]

LEET_MAP = {
    '0': 'o', '1': 'l', '3':'e', '4': 'a', '5': 's', '7': 't',
    '@': 'a', '$': 's', '!': 'i', '9': 'g'
}

# Set dictionary words to lowercase set

def load_word_set(paths):
    words = set()
    for p in paths:
        try:
            with open(p, "rt", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    w=line.strip().lower()
                    if len(w) >= MIN_DICT_WORD_LEN:
                        words.add(w)
        except (FileNotFoundError, PermissionError):
            continue
    return words

# Detecting repeated sequences of characters/weak password sequences

def obvious_patterns(password: str):
    pw = password.lower()
    issues = []
    if re.search(r"(.)\1\1\1", pw):
        issues.append("Password contains 4+ repeated characters")

    sequences = [
        "abcdefghijklmnopqrstuvwxyz"
        "qwertyuiopasdfghjklzxcvbnm"
        "1234567890"
        "password"
    ]
    for seq in sequences:
        for l in (4,5):
            for i in range(len(seq) - l + 1):
                chunk= seq[i:i + l]
                if chunk in pw or chunk[::-1] in pw:
                    issues.append(f"Password contains weak sequence '{chunk}'")
                    break
    return issues

# Detecting dictionary words including those with "leet" substitutions
# Uses the "LEET_MAP" list from above

def contains_dictionary(pw: str, wordset: set[str]) -> tuple[bool, str]:
    lower = pw.lower()
    for w in wordset:
        if len(w) < MIN_DICT_WORD_LEN:
            continue
        if w in lower:
            return True, f"contains dictionary word '{w}'"
    rev = lower[::-1]
    for w in wordset:
        if w in rev:
            return True, f"contains reversed dictionary word '{w}'"
    normalized_characters = []
    leet_changes = 0
    for ch in lower:
        if ch in LEET_MAP:
            normalized_characters.append(LEET_MAP[ch])
            leet_changes += 1
        else:
            normalized_characters.append(ch)
        normalized = "".join(normalized_characters)
        if leet_changes <= MAX_LEET_SUBSTITUTION:
            for w in wordset:
                if w in normalized:
                    return True, f"contains dictionary word '{w}'"
    return False, ""

# Checking password against simple parameters and returning reasons for rejection

def check_password_strength(pw: str, wordset: set[str]):
    reasons = []

    if len(pw) < MIN_LENGTH:
        reasons.append(f"Password too short (min {MIN_LENGTH})")

    hit, msg = contains_dictionary(pw, wordset)
    if hit:
        reasons.append(msg)

    reasons.extend(obvious_patterns(pw))

    categories = sum(bool(re.search(p,pw)) for p in [r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]"])
    if categories < 3 and len(pw) < 20:
        reasons.append("Too many similar characters")

    return reasons

# Using stdin to pass the user's password to the passwd command twice
# This sets the password for the bbuser account to the user's password given it passes all checks

def set_system_password(password: str):
    try:
        proc = subprocess.run(
            ["passwd"],
            input=(bbpassword + "\n" + password + "\n" + password + "\n").encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        print(proc.stdout.decode(errors="ignore"))
        if proc.returncode != 0:
            print(proc.stderr.decode(errors="ignore"))
            return False
        return True
    except Exception as e:
        print(f"Error running passwd: {e}")
        return False

def main():
# Preventing repeated execution:
    if MARKER.exists():
        print("Password already changed, exiting.")
        return


    print("Password change required for bbuser. Ensure that you will remember this password.")
    print("First input your current password once, then you will be prompted to input the new password twice")
    print("The minimum character length is 12. Please do not use any dictionary words or chains of repeated characters.")
    wordset = load_word_set(DEFAULT_DICT_FILES)

    while True:
        pw1 = getpass.getpass("Enter new password: ")
        pw2 = getpass.getpass("Re-enter new password: ")

        if pw1 != pw2:
            print("Passwords do not match. Try again.\n")
            continue

        reasons = check_password_strength(pw1, wordset)
        if reasons:
            print("Password too weak:")
            for r in reasons:
                print("-",r)
            print("\nPlease try again.\n")
            continue

        print("Password accepted. Updating bbuser password...\n")
        ok = set_system_password(pw1)
        if ok:
            print("Password has been updated.")
            sys.exit(0)
        else:
            print("Failed to update password. Try again.\n")
            continue

if __name__ == "__main__":
#    if os.getuid() != 0:
#       print("This script must be run as root.")
#       sys.exit(1)
    main()
