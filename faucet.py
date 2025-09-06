# faucet.py — Pharos Testnet Faucet (tampilan sederhana & rapi)

import requests
import json
import time
from typing import List, Dict, Optional, Tuple
from eth_account import Account
from eth_account.messages import encode_defunct

# ──( Konfigurasi API )───────────────────────────────────────────────────────────
BASE_URL = "https://api.pharosnetwork.xyz"
HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "authorization": "Bearer null",
    "content-length": "0",
    "origin": "https://testnet.pharosnetwork.xyz",
    "priority": "u=1, i",
    "referer": "https://testnet.pharosnetwork.xyz/",
    "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
}

# ──( Util tampilan )─────────────────────────────────────────────────────────────
def fmt_addr(addr: str) -> str:
    return addr if len(addr) <= 14 else f"{addr[:8]}…{addr[-4:]}"

def ok_json(data: dict) -> bool:
    # Umumnya API sukses: {"code":0, "data": {...}}
    return isinstance(data, dict) and data.get("code") == 0

def get_streak_from_status(data: dict) -> Optional[int]:
    """
    Coba ambil informasi 'streak' / hari berturut-turut dari response /sign/status
    Struktur pasti API bisa berubah; aman-kan akses.
    """
    try:
        d = data.get("data") or {}
        # Beberapa API pakai 'consecutiveDays' atau 'streak'
        for k in ("consecutiveDays", "streak", "continueDays", "days"):
            if k in d and isinstance(d[k], int):
                return d[k]
    except Exception:
        pass
    return None

def safe_get_msg(data: dict) -> str:
    # Ambil pesan yang human-friendly kalau ada
    if not isinstance(data, dict):
        return "-"
    if "msg" in data and isinstance(data["msg"], str):
        return data["msg"]
    if "message" in data and isinstance(data["message"], str):
        return data["message"]
    return "-"

# ──( HTTP helper )───────────────────────────────────────────────────────────────
def make_request(method: str, url: str, params=None, headers=None, retries=3, backoff=1.5):
    for attempt in range(retries):
        try:
            r = requests.request(method, url, params=params, headers=headers, timeout=15)
            if r.status_code in (200, 201):
                return r
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(backoff ** attempt)
    return None

# ──( File utils )────────────────────────────────────────────────────────────────
def read_private_keys(filename: str = "privatekey.txt") -> List[str]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except FileNotFoundError:
        print("❌ File privatekey.txt tidak ditemukan")
        return []

def read_invite_code(filename: str = "reff.txt") -> Optional[str]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            code = f.read().strip()
            return code or None
    except FileNotFoundError:
        return None

# ──( Auth )──────────────────────────────────────────────────────────────────────
def generate_signature(private_key: str, message: str = "pharos") -> Tuple[Optional[str], Optional[str]]:
    try:
        acct = Account.from_key(private_key)
        msg = encode_defunct(text=message)
        sig = acct.sign_message(msg).signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig
        return acct.address, sig
    except Exception:
        return None, None

def login(address: str, signature: str) -> Optional[str]:
    url = f"{BASE_URL}/user/login"
    resp = make_request("POST", url, params={"address": address, "signature": signature}, headers=HEADERS_BASE)
    if not resp:
        return None
    try:
        data = resp.json()
        if ok_json(data):
            return (data.get("data") or {}).get("jwt")
    except Exception:
        pass
    return None

def api_with_jwt(path: str, method: str, jwt: str, address: str):
    url = f"{BASE_URL}{path}"
    headers = {**HEADERS_BASE, "authorization": f"Bearer {jwt}"}
    resp = make_request(method, url, params={"address": address}, headers=headers)
    try:
        return resp.json() if resp else None
    except Exception:
        return None

# ──( Pipeline per akun )─────────────────────────────────────────────────────────
def process_account(pk: str, idx: int, total: int) -> Dict[str, Optional[str]]:
    """
    Kembalikan ringkasan: {
      'addr': '0x..',
      'login': '✓/✗',
      'signin': '✓/✗',
      'streak': 'n / -',
      'faucet': '✓/✗',
      'note': 'pesan singkat'
    }
    """
    summary = {"addr": "-", "login": "✗", "signin": "✗", "streak": "-", "faucet": "✗", "note": "-"}
    try:
        acct = Account.from_key(pk)
        addr = acct.address
        summary["addr"] = fmt_addr(addr)
    except Exception:
        summary["note"] = "PK invalid"
        return summary

    # Login
    address, sig = generate_signature(pk)
    if not (address and sig):
        summary["note"] = "Sign message gagal"
        return summary
    jwt = login(address, sig)
    if not jwt:
        summary["note"] = "Login gagal"
        return summary
    summary["login"] = "✓"

    # Sign-in harian
    res_signin = api_with_jwt("/sign/in", "POST", jwt, address)
    if ok_json(res_signin):
        summary["signin"] = "✓"
    else:
        summary["signin"] = "✗"

    # Status (ambil streak jika ada)
    res_status = api_with_jwt("/sign/status", "GET", jwt, address)
    st = get_streak_from_status(res_status or {})
    if st is not None:
        summary["streak"] = str(st)

    # Faucet daily
    res_faucet = api_with_jwt("/faucet/daily", "POST", jwt, address)
    if ok_json(res_faucet):
        summary["faucet"] = "✓"
        summary["note"] = "OK"
    else:
        # tampilkan pesan singkat biar tahu kenapa gagal (mis. cooldown)
        summary["note"] = safe_get_msg(res_faucet or {})
    return summary

# ──( Runner )────────────────────────────────────────────────────────────────────
def print_header():
    title = "PHAROS FAUCET — SIMPLE RUN"
    print("\n" + title)
    print("-" * len(title))

def print_table(rows: List[Dict[str, str]]):
    # Kolom: # | Address | Login | Sign-in | Streak | Faucet | Note
    headers = ["#", "Address", "Login", "Sign-in", "Streak", "Faucet", "Note"]
    widths = [4, 16, 7, 9, 8, 8, 30]

    def fmt_row(cols, widths):
        return " ".join(str(c).ljust(w) for c, w in zip(cols, widths))

    print(fmt_row(headers, widths))
    print(fmt_row(["─"*w for w in widths], widths))

    for i, r in enumerate(rows, 1):
        print(fmt_row([
            i,
            r.get("addr", "-"),
            r.get("login", "-"),
            r.get("signin", "-"),
            r.get("streak", "-"),
            r.get("faucet", "-"),
            (r.get("note", "-") or "-")[:widths[-1]],
        ], widths))

def print_summary(rows: List[Dict[str, str]]):
    total = len(rows)
    log_ok = sum(1 for r in rows if r.get("login") == "✓")
    si_ok = sum(1 for r in rows if r.get("signin") == "✓")
    fc_ok = sum(1 for r in rows if r.get("faucet") == "✓")
    print("\nSummary:")
    print(f"  Accounts   : {total}")
    print(f"  Login OK   : {log_ok}")
    print(f"  Sign-in OK : {si_ok}")
    print(f"  Faucet OK  : {fc_ok}\n")

def run_once():
    private_keys = read_private_keys()
    if not private_keys:
        return

    print_header()
    rows = []
    for idx, pk in enumerate(private_keys, 1):
        row = process_account(pk, idx, len(private_keys))
        rows.append(row)
        # jeda pendek untuk jaga-jaga rate limit
        time.sleep(0.3)

    print_table(rows)
    print_summary(rows)

def run_loop(interval_sec: int = 3600):
    while True:
        run_once()
        hrs = max(1, interval_sec // 3600)
        print(f"Menunggu {hrs} jam untuk siklus berikutnya…\n")
        time.sleep(interval_sec)

def main(loop: bool = False, interval_sec: int = 3600):
    if loop:
        run_loop(interval_sec)
    else:
        run_once()

if __name__ == "__main__":
    # Default: sekali jalan agar output ringkas
    main(loop=False, interval_sec=3600)
