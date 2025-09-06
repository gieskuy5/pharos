import requests
import json
from eth_account.messages import encode_defunct
from web3 import Web3  # (dipakai untuk tipe/kompat, biarkan)
import time
from eth_account import Account
import random

# ====== Konfigurasi API ======
BASE_URL = "https://api.pharosnetwork.xyz"
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'authorization': 'Bearer null',
    'content-length': '0',
    'origin': 'https://testnet.pharosnetwork.xyz',
    'priority': 'u=1, i',
    'referer': 'https://testnet.pharosnetwork.xyz/',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
}

# ====== HTTP helper ======
def make_request(method, url, params=None, headers=None, retries=5, backoff_factor=1.5):
    for attempt in range(retries):
        try:
            response = requests.request(method, url, params=params, headers=headers, timeout=15)
            if response.status_code in [200, 201]:
                return response
            print(f"⚠️ Request failed with status {response.status_code}, attempt {attempt + 1}/{retries}")
        except Exception as e:
            print(f"⚠️ Request error: {str(e)}, attempt {attempt + 1}/{retries}")
        if attempt < retries - 1:
            wait_time = backoff_factor ** attempt
            print(f"⏳ Waiting {wait_time:.1f} seconds before retry...")
            time.sleep(wait_time)
    return None

# ====== File utils ======
def read_private_keys(filename="privatekey.txt"):
    try:
        with open(filename, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found")
        return []

def read_invite_code(filename="reff.txt"):
    try:
        with open(filename, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found")
        return "fgi8ZeVTz5WQEm2X"  # fallback

# ====== Auth & aksi ======
def generate_signature(private_key, message="pharos"):
    try:
        acct = Account.from_key(private_key)
        message_encoded = encode_defunct(text=message)
        signed = acct.sign_message(message_encoded)
        signature = signed.signature.hex()
        if not signature.startswith("0x"):
            signature = "0x" + signature
        return acct.address, signature
    except Exception as e:
        print(f"❌ Error generating signature: {str(e)}")
        return None, None

def login(address, signature):
    url = f"{BASE_URL}/user/login"
    params = {"address": address, "signature": signature}
    response = make_request('POST', url, params=params, headers=HEADERS)
    if response:
        try:
            data = response.json()
            if data.get("code") == 0:
                return data["data"]["jwt"]
        except Exception:
            pass
    return None

def sign_in(address, jwt_token):
    url = f"{BASE_URL}/sign/in"
    params = {"address": address}
    headers = {**HEADERS, "authorization": f"Bearer {jwt_token}"}
    response = make_request('POST', url, params=params, headers=headers)
    return response.json() if response else None

def check_sign_status(address, jwt_token):
    url = f"{BASE_URL}/sign/status"
    params = {"address": address}
    headers = {**HEADERS, "authorization": f"Bearer {jwt_token}"}
    response = make_request('GET', url, params=params, headers=headers)
    return response.json() if response else None

def claim_daily_faucet(address, jwt_token):
    url = f"{BASE_URL}/faucet/daily"
    params = {"address": address}
    headers = {**HEADERS, "authorization": f"Bearer {jwt_token}"}
    response = make_request('POST', url, params=params, headers=headers)
    return response.json() if response else None

# ====== Pipeline per akun ======
def process_account(private_key, current_number, total_accounts):
    try:
        print(f"\n🔄 Memproses PK {current_number}/{total_accounts}")
        address, signature = generate_signature(private_key)
        if not address or not signature:
            print("❌ Failed to generate signature")
            return

        print(f"📝 Address: {address}")
        jwt_token = login(address, signature)
        if not jwt_token:
            print("❌ Failed to login")
            return

        sign_in_result = sign_in(address, jwt_token)
        print(f"📤 Sign in result: {sign_in_result}")

        status_result = check_sign_status(address, jwt_token)
        print(f"📊 Sign status: {status_result}")

        faucet_result = claim_daily_faucet(address, jwt_token)
        print(f"💰 Faucet claim result: {faucet_result}")

        time.sleep(1)
    except Exception as e:
        print(f"❌ Error processing account: {str(e)}")

# ====== Runner ======
def run_once():
    private_keys = read_private_keys()
    if not private_keys:
        print("❌ No private keys found")
        return
    total = len(private_keys)
    print(f"📊 Total PK yang akan diproses: {total}")
    for idx, pk in enumerate(private_keys, 1):
        process_account(pk, idx, total)

def run_loop(interval_sec: int = 3600):
    while True:
        run_once()
        print(f"\n⏳ Semua akun selesai. Menunggu {interval_sec//3600} jam sebelum ulangi...")
        time.sleep(interval_sec)

def main(loop: bool = True, interval_sec: int = 3600):
    if loop:
        run_loop(interval_sec)
    else:
        run_once()

if __name__ == "__main__":
    # Default: loop per jam seperti skrip asli
    main(loop=True, interval_sec=3600)
