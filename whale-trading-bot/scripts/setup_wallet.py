#!/usr/bin/env python3
"""Wallet setup utility"""

import json
import base58
from solders.keypair import Keypair

def generate_wallet():
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    private_key_base58 = base58.b58encode(bytes(keypair)).decode()
    
    print(f" New wallet generated:")
    print(f"   Address: {public_key}")
    print(f"   Private Key: {private_key_base58}")
    print(f"   Add to .env: SOLANA_PRIVATE_KEY={private_key_base58}")
    
    return {"address": public_key, "private_key": private_key_base58}

if __name__ == "__main__":
    generate_wallet()
