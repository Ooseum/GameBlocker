"""
GameBlocker - shared core logic.

State model:
  * Games start UNLOCKED.
  * Locking is free and indefinite (set locked=True).
  * Unlocking requires the family code (3 different people's numbers, any order).

Family numbers are stored as salted PBKDF2 hashes. Honest note: a 1-3 digit
number has only ~1110 possible values, so the hash is obfuscation, not real
protection, against an administrator who can read the config. The real lock in
the family-admin design is account privilege + file permissions. See README.
"""

import json
import os
import secrets
import hashlib
import itertools

CONFIG_DIR = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "GameBlocker")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
# the service writes the last blocked game here; the notifier watches it
LAST_BLOCK_PATH = os.path.join(CONFIG_DIR, "last_block.json")

DEFAULT_BLOCKLIST = [
    "RobloxPlayerBeta.exe",
    "steam.exe",
    "FortniteClient-Win64-Shipping.exe",
    "Overwatch.exe",
    "EpicGamesLauncher.exe",
    "Battle.net.exe",
    "LeagueClient.exe",
    "RiotClientServices.exe",
    "Minecraft.exe",
]

PBKDF_ITERS = 200_000
MIN_ENROLLED = 3
DEFAULT_THEME = "Daylight"


def _default_config():
    return {
        "enrolled": [],
        "blocklist": list(DEFAULT_BLOCKLIST),
        "locked": False,
        "theme": DEFAULT_THEME,
    }


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return _default_config()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # fill any missing keys (forward-compatible with older config files)
    base = _default_config()
    for k, v in base.items():
        cfg.setdefault(k, v)
    return cfg


def save_config(cfg):
    """Atomic write so a crash mid-save can't corrupt the config."""
    _ensure_dir()
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_PATH)


def hash_number(number: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", number.encode("utf-8"), salt, PBKDF_ITERS).hex()


def enroll(cfg, name: str, number: str):
    number = number.strip()
    if not number.isdigit() or not (1 <= len(number) <= 3):
        raise ValueError("Number must be 1-3 digits.")
    salt = secrets.token_bytes(16)
    cfg["enrolled"].append(
        {"name": name.strip(), "salt": salt.hex(), "hash": hash_number(number, salt)}
    )


def set_number(cfg, index: int, number: str):
    """Replace an enrolled person's number (new salt + hash). Keeps their name."""
    number = number.strip()
    if not number.isdigit() or not (1 <= len(number) <= 3):
        raise ValueError("Number must be 1-3 digits.")
    salt = secrets.token_bytes(16)
    cfg["enrolled"][index]["salt"] = salt.hex()
    cfg["enrolled"][index]["hash"] = hash_number(number, salt)


def _matches_member(part: str, member: dict) -> bool:
    salt = bytes.fromhex(member["salt"])
    return hash_number(part, salt) == member["hash"]


def valid_unlock(cfg, big_code: str) -> bool:
    """
    True if big_code splits into 3 parts (each 1-3 digits) matching 3 distinct
    enrolled people, in any order. e.g. {14,12,13} -> 141213 / 121314 / 131412.
    """
    enrolled = cfg.get("enrolled", [])
    big_code = (big_code or "").strip()
    if len(enrolled) < MIN_ENROLLED or not big_code.isdigit():
        return False
    L = len(big_code)
    for i in range(1, 4):
        for j in range(1, 4):
            k = L - i - j
            if not (1 <= k <= 3):
                continue
            parts = [big_code[:i], big_code[i:i + j], big_code[i + j:]]
            match_sets = [
                {idx for idx, m in enumerate(enrolled) if _matches_member(p, m)}
                for p in parts
            ]
            if any(len(s) == 0 for s in match_sets):
                continue
            for combo in itertools.permutations(range(len(enrolled)), 3):
                if all(combo[t] in match_sets[t] for t in range(3)):
                    return True
    return False


# ---- lock state ----
def is_locked(cfg) -> bool:
    # Only locked when the lock flag is set AND there are enough people to ever
    # unlock it. A fresh run (0 enrolled) is therefore always unlocked, and you
    # can never get stuck locked with fewer than MIN_ENROLLED people.
    return bool(cfg.get("locked", False)) and len(cfg.get("enrolled", [])) >= MIN_ENROLLED


def lock(cfg):
    cfg["locked"] = True
    save_config(cfg)


def unlock(cfg):
    cfg["locked"] = False
    save_config(cfg)
