from web3 import Web3
from eth_account import Account
import time
import json
import re
from datetime import datetime

# ====== Konfigurasi ======
RPC_URL = "https://testnet.dplabs-internal.com"
w3 = Web3(Web3.HTTPProvider(RPC_URL))
chain_id = w3.eth.chain_id

# ====== Util ======
def validate_private_key(key: str):
    key = key.strip()
    if key.startswith('0x'):
        key = key[2:]
    key = ''.join(key.split())
    if len(key) != 64 or not re.match(r'^[0-9a-fA-F]+$', key):
        return None
    return key

def load_private_keys(path: str = "privatekey.txt"):
    valid_keys = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.read().split('\n') if line.strip()]

        for i, line in enumerate(lines, 1):
            cleaned_key = validate_private_key(line)
            if cleaned_key:
                try:
                    test_account = Account.from_key(cleaned_key)
                    valid_keys.append(cleaned_key)
                    print(f"✅ Wallet {i}: {test_account.address[:8]}...")
                except Exception:
                    print(f"❌ Wallet {i}: Invalid")
            else:
                print(f"❌ Wallet {i}: Invalid format")
    except FileNotFoundError:
        print("❌ File privatekey.txt tidak ditemukan!")
        return []
    return valid_keys

# ====== Kontrak NFT ======
nft_contracts = [
    {"name": "NFT 1", "address": "0x1da9f40036bee3fda37ddd9bff624e1125d8991d"},
    {"name": "NFT 2", "address": "0x2a469a4073480596b9deb19f52aa89891ccff5ce"},
    {"name": "NFT 3", "address": "0xe71188df7be6321ffd5aaa6e52e6c96375e62793"},
    {"name": "NFT 4", "address": "0xb2ac4f09735007562c513ebbe152a8d7fa682bef"},
    {"name": "NFT 5", "address": "0x96381ed3fcfb385cbacfe6908159f0905b19767a"},
    {"name": "NFT 6", "address": "0x0d00314d006e70ca08ac37c3469b4bf958a7580b"},
    {"name": "NFT 7", "address": "0x4af366c7269dc9a0335bd055af979729c20e0f5f"},
    {"name": "NFT 8", "address": "0x9979b7fedf761c2989642f63ba6ed580dbdfc46f"},
    {"name": "NFT 9", "address": "0x822483f6cf39b7dad66fec5f4feecbfd72172626"},  # NFT baru
]

contract_abi = [
    {
        "inputs": [
            {"internalType": "address", "name": "_receiver", "type": "address"},
            {"internalType": "uint256", "name": "_quantity", "type": "uint256"},
            {"internalType": "address", "name": "_currency", "type": "address"},
            {"internalType": "uint256", "name": "_pricePerToken", "type": "uint256"},
            {
                "components": [
                    {"internalType": "bytes32[]", "name": "proof", "type": "bytes32[]"},
                    {"internalType": "uint256", "name": "quantityLimitPerWallet", "type": "uint256"},
                    {"internalType": "uint256", "name": "pricePerToken", "type": "uint256"},
                    {"internalType": "address", "name": "currency", "type": "address"}
                ],
                "internalType": "struct IDrop.AllowlistProof",
                "name": "_allowlistProof",
                "type": "tuple"
            },
            {"internalType": "bytes", "name": "_data", "type": "bytes"}
        ],
        "name": "claim",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ====== Statistik ======
stats = {
    "total_minted": 0,
    "total_failed": 0,
    "total_gas_used": 0,
    "errors": {}
}

# ====== Fungsi Minting ======
def check_nft_balance(contract, address):
    try:
        return contract.functions.balanceOf(address).call()
    except Exception as e:
        print(f"   ⚠️  Error checking balance: {str(e)[:50]}...")
        return 0

def get_gas_price():
    try:
        gas_price = w3.eth.gas_price
        return int(gas_price * 1.1)  # buffer 10%
    except Exception:
        return w3.to_wei(1, 'gwei')

def estimate_gas(contract, wallet_address, receiver, quantity, currency, price_per_token, allowlist_proof, data, value):
    try:
        estimated = contract.functions.claim(
            receiver, quantity, currency, price_per_token, allowlist_proof, data
        ).estimate_gas({'from': wallet_address, 'value': value})
        return int(estimated * 1.2)  # buffer 20%
    except Exception:
        return 250000

def mint_nft(contract_address, wallet_address, private_key, nft_name, retry_count=0):
    max_retries = 2
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi
        )
        receiver = Web3.to_checksum_address(wallet_address)
        quantity = 1
        currency = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        price_per_token = w3.to_wei(1, 'ether')  # ganti sesuai kebutuhanmu

        allowlist_proof = ([], 2**256 - 1, 0, "0x0000000000000000000000000000000000000000")
        data = "0x"

        nonce = w3.eth.get_transaction_count(wallet_address)
        total_value = price_per_token * quantity

        gas_price = get_gas_price()
        gas_limit = estimate_gas(
            contract, wallet_address, receiver, quantity,
            currency, price_per_token, allowlist_proof, data, total_value
        )

        tx = contract.functions.claim(
            receiver, quantity, currency, price_per_token, allowlist_proof, data
        ).build_transaction({
            'from': wallet_address,
            'value': total_value,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': chain_id,
            'gas': gas_limit
        })

        total_cost = total_value + (gas_limit * gas_price)
        eth_cost = w3.from_wei(total_cost, 'ether')
        print(f"   💸 Estimated cost: {eth_cost:.4f} ETH (Gas: {gas_limit})")

        balance = w3.eth.get_balance(wallet_address)
        if balance < total_cost:
            print(f"   ❌ Insufficient balance untuk {nft_name}")
            stats["total_failed"] += 1
            return False

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        raw_tx = getattr(signed_tx, "rawTransaction", None) or getattr(signed_tx, "raw_transaction", None)

        print(f"   📤 Sending TX untuk {nft_name}...")
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        print(f"   🔍 TX Hash: {tx_hash.hex()}")
        print(f"   ⏳ Menunggu konfirmasi...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        if receipt.status == 1:
            gas_used = receipt.gasUsed
            gas_cost = w3.from_wei(gas_used * gas_price, 'ether')
            print(f"   ✅ {nft_name} minted!")
            print(f"   ⛽ Gas used: {gas_used} ({gas_cost:.4f} ETH)")
            stats["total_minted"] += 1
            stats["total_gas_used"] += gas_used
            return True
        else:
            print(f"   ❌ {nft_name} tx failed!")
            stats["total_failed"] += 1
            key = f"{nft_name}_failed"
            stats["errors"][key] = stats["errors"].get(key, 0) + 1
            if retry_count < max_retries:
                print(f"   🔄 Retry {nft_name} ({retry_count + 2}/{max_retries + 1})...")
                time.sleep(3)
                return mint_nft(contract_address, wallet_address, private_key, nft_name, retry_count + 1)
            return False

    except Exception as e:
        msg = str(e)
        print(f"   ❌ {nft_name} error: {msg[:100]}...")
        if "insufficient funds" in msg.lower():
            stats["errors"]["insufficient_funds"] = stats["errors"].get("insufficient_funds", 0) + 1
        elif "nonce too low" in msg.lower():
            stats["errors"]["nonce_error"] = stats["errors"].get("nonce_error", 0) + 1
        else:
            stats["errors"]["other"] = stats["errors"].get("other", 0) + 1
        stats["total_failed"] += 1
        if retry_count < max_retries and "nonce" not in msg.lower():
            print(f"   🔄 Retry {nft_name} ({retry_count + 2}/{max_retries + 1})...")
            time.sleep(5)
            return mint_nft(contract_address, wallet_address, private_key, nft_name, retry_count + 1)
        return False

def process_wallet(wallet_index: int, private_key: str):
    try:
        account = Account.from_key(private_key)
        wallet_address = account.address
    except Exception:
        print(f"❌ Wallet {wallet_index}: Private key invalid")
        return

    print(f"🎯 Wallet {wallet_index}: {wallet_address}")
    eth_balance = w3.eth.get_balance(wallet_address)
    eth_amount = w3.from_wei(eth_balance, 'ether')
    print(f"   💰 Balance: {eth_amount:.4f} ETH")

    if eth_balance < w3.to_wei(0.1, 'ether'):
        print(f"   ❌ Balance kurang (min 0.1 ETH)")
        return

    owned_nfts, missing_nfts = [], []
    print(f"   🔍 Cek NFT yang sudah dimiliki...")
    for nft_info in nft_contracts:
        try:
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(nft_info["address"]),
                abi=contract_abi
            )
            owned_bal = check_nft_balance(contract, wallet_address)
            if owned_bal > 0:
                owned_nfts.append(nft_info["name"])
            else:
                missing_nfts.append(nft_info)
        except Exception as e:
            print(f"   ⚠️  Error cek {nft_info['name']}: {str(e)[:50]}...")
            missing_nfts.append(nft_info)

    if owned_nfts:
        print(f"   ✅ Sudah punya: {', '.join(owned_nfts)}")

    if not missing_nfts:
        print(f"   🎉 Semua NFT sudah dimiliki!")
        return

    print(f"   🔄 Perlu mint: {len(missing_nfts)} NFT")
    minted, failed = 0, 0
    for i, nft_info in enumerate(missing_nfts, 1):
        print(f"\n   📍 Minting {nft_info['name']} ({i}/{len(missing_nfts)})")
        ok = mint_nft(nft_info["address"], wallet_address, private_key, nft_info["name"])
        if ok:
            minted += 1
            time.sleep(3)
        else:
            failed += 1
            time.sleep(2)
    print(f"\n   📊 Ringkasan wallet: {minted} minted, {failed} gagal")

def print_final_stats():
    print("\n" + "="*50)
    print("📊 FINAL STATISTICS")
    print("="*50)
    print(f"✅ Total NFTs minted: {stats['total_minted']}")
    print(f"❌ Total failed: {stats['total_failed']}")
    if stats['total_gas_used'] > 0 and stats['total_minted'] > 0:
        avg_gas = stats['total_gas_used'] / stats['total_minted']
        print(f"⛽ Average gas per mint: {avg_gas:,.0f}")
    if stats['errors']:
        print("\n🚨 Error Summary:")
        for k, v in stats['errors'].items():
            print(f"   - {k}: {v}")
    print(f"\n⏱️  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

def main(delay_between_wallets_sec: int = 5):
    print(f"🔗 Chain ID: {chain_id}")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print("🚀 Starting NFT minting process...\n")

    private_keys = load_private_keys()
    if not private_keys:
        return

    try:
        for i, pk in enumerate(private_keys, 1):
            process_wallet(i, pk)
            if i < len(private_keys):
                print(f"\n⏳ Next wallet in {delay_between_wallets_sec} seconds...")
                print("-"*50 + "\n")
                time.sleep(delay_between_wallets_sec)
            else:
                print("")
        print("🎉 All wallets processed!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Dihentikan oleh user!")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
    finally:
        print_final_stats()

if __name__ == "__main__":
    main()
