"""
Generate weak Bitcoin addresses using known PRNG seeds for testing.
These addresses WILL be crackable by the scanner.
"""
import random
import json
from datetime import datetime
from bitcoinlib.keys import Key

def generate_private_key_from_seed(seed):
    """Generate private key using MT19937 with given seed."""
    rng = random.Random(seed)
    key_bytes = bytes([rng.randint(0, 255) for _ in range(32)])
    return key_bytes

def create_weak_addresses(num_addresses=10):
    """Create weak addresses with known seeds."""
    addresses = []
    
    for seed in range(1, num_addresses + 1):
        # Generate private key from weak seed
        private_key = generate_private_key_from_seed(seed)
        
        # Create Bitcoin testnet key
        key = Key(private_key.hex(), network='testnet')
        address = key.address()
        
        # Create address entry
        entry = {
            "address": address,
            "block_height": 4750533,
            "block_hash": "00000000000833a80bca5e3d618793e104155546ce3b7be88735e70703d311ea",
            "transaction": f"weak_key_test_{seed:03d}",
            "collected_at": datetime.now().isoformat(),
            "entropy_score": 4.5,
            "is_suspicious": True,
            "analysis": {
                "shannon_entropy": 4.5,
                "chi_square_p": 0.001,
                "hash_entropy": 4.3
            },
            "patterns": ["low_entropy"],
            "metadata": {
                "weak_seed": seed,
                "test_address": True,
                "expected_recovery": True
            }
        }
        
        addresses.append(entry)
        print(f"✓ Generated weak address #{seed}: {address} (seed={seed})")
    
    return addresses

if __name__ == "__main__":
    print("Generating 10 WEAK addresses with known PRNG seeds...")
    print("=" * 70)
    
    weak_addresses = create_weak_addresses(10)
    
    # Create checkpoint with weak addresses
    checkpoint = {
        "timestamp": datetime.now().isoformat(),
        "addresses_processed": 10,
        "weak_found": 10,
        "keys_recovered": 0,
        "addresses_analyzed": weak_addresses
    }
    
    # Save to checkpoint
    with open('checkpoint_weak.json', 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print("=" * 70)
    print(f"✓ Created checkpoint_weak.json with {len(weak_addresses)} crackable addresses")
    print("\nThese addresses use seeds 1-10 (within our 65,536 search space)")
    print("The scanner WILL successfully recover these keys!")
    print("\nTo use: Copy checkpoint_weak.json to checkpoint.json")
