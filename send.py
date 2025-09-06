#!/usr/bin/env python3
# send.py — Auto Send PHRS (Pharos Testnet)
# Fitur:
# - Pilih privatekey pengirim (dari privatekey.txt)
# - Masukkan amount (PHRS) → dikirim ke SEMUA address lain
# - Cek saldo & gas, kirim berurutan dengan nonce yang benar
# - Log hasil ringkas di akhir

import sys
import time
import re
from decimal import Decimal, InvalidOperation
from typing import List, Tuple
from web3 import Web3
from eth_account import Account

# ===== Konfigurasi jaringan =====
RPC_URL = "https://testnet.dplabs-internal.com"  # Pharos Testnet
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    print("❌ Gagal konek RPC. Cek internet/RPC_URL.")
    sys.exit(1)

CHAIN_ID = w3.eth.chain_id
NATIVE_SYMBOL = "PHRS"

# ===== Util =====
def validate_private_key(key: str) -> str | None:
    key = key.strip()
    if key.startswith("0x"):
        key = key[2:]
    key = "".join(key.split())
    if len(key) != 64 or not re.match(r"^[0-9a-fA-F]+$", key):
        return None
    return "0x" + key

def load_private_keys(path: str = "privatekey.txt") -> List[str]:
    keys: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                cleaned = validate_private_key(line)
                if cleaned:
                    keys.append(cleaned)
                else:
                    print(f"⚠️  Lewati baris invalid di privatekey.txt: {line.strip()[:10]}...")
    except FileNotFoundError:
        print("❌ privatekey.txt tidak ditemukan.")
        return []
    return keys

def to_checksum(addr: str) -> str:
    return Web3.to_checksum_address(addr)

def fmt_addr(addr: str) -> str:
    return f"{addr[:8]}…{addr[-6:]}"

def ask_int(prompt: str, min_val: int, max_val: int) -> int:
    while True:
        s = input(prompt).strip()
        if s.isdigit():
            val = int(s)
            if min_val <= val <= max_val:
                return val
        print(f"Masukkan angka {min_val}-{max_val} yang valid.")

def ask_amount(prompt: str) -> Decimal:
    while True:
        s = input(prompt).strip()
        try:
            val = Decimal(s)
            if val > 0:
                return val
        except InvalidOperation:
            pass
        print("Masukkan amount numerik > 0 (contoh: 0.001).")

def get_gas_price() -> int:
    try:
        gp = w3.eth.gas_price
        # buffer 10%
        return int(gp * 1.1)
    except Exception:
        # fallback 1 gwei
        return w3.to_wei(1, "gwei")

def ensure_balance_enough(sender_addr: str, recipients: int, amount_wei: int, gas_price: int, gas_limit: int = 21000) -> Tuple[bool, str]:
    bal = w3.eth.get_balance(sender_addr)
    total_value = amount_wei * recipients
    total_gas = gas_price * gas_limit * recipients
    need = total_value + total_gas
    if bal < need:
        short = need - bal
        return (False, f"Saldo tidak cukup. Perlu ~{w3.from_wei(need, 'ether')} {NATIVE_SYMBOL}, saldo {w3.from_wei(bal, 'ether')} {NATIVE_SYMBOL}. Kurang {w3.from_wei(short, 'ether')} {NATIVE_SYMBOL}.")
    return (True, "")

def main():
    print(f"🔗 Chain ID: {CHAIN_ID}  |  RPC: {RPC_URL}")
    print("🚀 Auto Send PHRS — pilih pengirim & kirim ke semua wallet lain\n")

    # 1) Load & tampilkan daftar wallet
    pks = load_private_keys()
    if len(pks) < 2:
        print("❌ Minimal butuh 2 private key di privatekey.txt (pengirim + penerima).")
        sys.exit(1)

    accounts = []
    for pk in pks:
        try:
            acct = Account.from_key(pk)
            accounts.append((pk, acct.address))
        except Exception:
            print("⚠️  PK invalid, lewati.")
    if len(accounts) < 2:
        print("❌ Tidak ada cukup PK valid.")
        sys.exit(1)

    print("📜 Daftar wallet:")
    for i, (_, addr) in enumerate(accounts, 1):
        bal = w3.from_wei(w3.eth.get_balance(addr), "ether")
        print(f"  {i:>2}. {fmt_addr(addr)}  |  {bal:.6f} {NATIVE_SYMBOL}")

    # 2) Pilih pengirim
    idx = ask_int(f"\nPilih nomor wallet sebagai PENGIRIM (1-{len(accounts)}): ", 1, len(accounts))
    sender_pk, sender_addr = accounts[idx - 1]
    recipients = [addr for i, (_, addr) in enumerate(accounts, 1) if i != idx]

    print(f"\n👤 Pengirim : {sender_addr}  ({fmt_addr(sender_addr)})")
    print(f"🎯 Penerima : {len(recipients)} wallet")

    # 3) Masukkan amount PHRS per penerima
    amount_phrs = ask_amount(f"Masukkan amount per penerima ({NATIVE_SYMBOL}, contoh 0.001): ")
    amount_wei = int(w3.to_wei(amount_phrs, "ether"))

    # 4) Cek saldo & gas
    gas_price = get_gas_price()
    ok, msg = ensure_balance_enough(sender_addr, len(recipients), amount_wei, gas_price, 21000)
    if not ok:
        print(f"❌ {msg}")
        sys.exit(1)

    # 5) Konfirmasi
    total_value_phrs = amount_phrs * Decimal(len(recipients))
    est_gas_phrs = Decimal(w3.from_wei(gas_price * 21000 * len(recipients), "ether"))
    print("\n🧮 Ringkasan:")
    print(f"  Kirim      : {total_value_phrs} {NATIVE_SYMBOL} (={amount_phrs} x {len(recipients)} wallet)")
    print(f"  Est. Gas   : ~{est_gas_phrs} {NATIVE_SYMBOL}  (gasPrice {w3.from_wei(gas_price, 'gwei'):.2f} gwei)")
    go = input("Lanjut kirim? (y/N): ").strip().lower()
    if go != "y":
        print("⏹  Dibatalkan.")
        sys.exit(0)

    # 6) Kirim berurutan (nonce manual)
    sender_acct = Account.from_key(sender_pk)
    current_nonce = w3.eth.get_transaction_count(sender_addr)
    success, failed = 0, 0
    tx_hashes = []

    print("\n📤 Mengirim transaksi:")
    for i, to_addr in enumerate(recipients, 1):
        try:
            tx = {
                "to": to_checksum(to_addr),
                "value": amount_wei,
                "gas": 21000,
                "gasPrice": gas_price,
                "nonce": current_nonce,
                "chainId": CHAIN_ID,
            }
            signed = w3.eth.account.sign_transaction(tx, private_key=sender_pk)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            txh = tx_hash.hex()
            tx_hashes.append(txh)
            print(f"  [{i}/{len(recipients)}] → {fmt_addr(to_addr)} | TX: {txh}")
            current_nonce += 1

            # (Opsional) tunggu sebentar agar RPC nyaman; hindari rate limit
            time.sleep(0.3)
            success += 1
        except Exception as e:
            print(f"  [{i}/{len(recipients)}] → {fmt_addr(to_addr)} | ❌ Gagal: {str(e)[:120]}...")
            failed += 1
            # Jika error nonce/gas price, coba lanjut ke berikutnya

    # 7) Rekap
    print("\n" + "=" * 70)
    print("📊 RINGKASAN PENGIRIMAN")
    print("=" * 70)
    print(f"Pengirim        : {sender_addr}")
    print(f"Total penerima  : {len(recipients)}")
    print(f"Berhasil        : {success}")
    print(f"Gagal           : {failed}")
    if tx_hashes:
        print("\n🔗 TX Hash:")
        for h in tx_hashes:
            print(f"  - {h}")
    print("\nSelesai ✅")

if __name__ == "__main__":
    main()
