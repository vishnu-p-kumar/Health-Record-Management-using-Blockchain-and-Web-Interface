import hashlib
import json
from time import time
from Crypto.Hash import SHA256
from typing import List, Dict

class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: float, previous_hash: str):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            'index': self.index,
            'transactions': self.transactions,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int) -> None:
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.difficulty = 2
        self.pending_transactions = []
        self.mining_reward = 0

    def create_genesis_block(self) -> Block:
        return Block(0, [], time(), "0")

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, sender: str, recipient: str, data: Dict) -> None:
        self.pending_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'data': data,
            'timestamp': time()
        })

    def mine_pending_transactions(self, miner_address: str) -> Block:
        block = Block(
            len(self.chain),
            self.pending_transactions,
            time(),
            self.get_latest_block().hash
        )
        
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending_transactions = []
        return block

    def get_patient_records(self, patient_id: str) -> List[Dict]:
        records = []
        for block in self.chain:
            for transaction in block.transactions:
                if transaction['recipient'] == patient_id:
                    records.append({
                        'sender': transaction['sender'],
                        'data': transaction['data'],
                        'timestamp': transaction['timestamp']
                    })
        return records

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

        return True
