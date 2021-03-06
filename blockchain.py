import hashlib
import json
from textwrap import dedent
from time import time
from urllib.parse import urlparse
import requests


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # Create the genesis block
        self.new_block(proof=100, previous_hash=1)

        # Create an empty set of nodes, ensures no duplicates
        self.nodes = set()


    def register_node(self, address):
        """
        Add a new node to the list of nodes

        address <str> -- Address of the node (e.g 'http://192.168.0.5:5000')

        """

        # Parse the adress
        parsed_url = urlparse(address)

        # Add the network location of the address to the list of nodes
        self.nodes.add(parsed_url.netloc)


    def new_block(self, proof, previous_hash=None):
        """
        Creates a new Block in the Blockchain

        proof <int> -- The proof given by the Proof of Work algorithm
        previous_hash <str> -- Hash of previous Block (Optional)

        return <dict> -- New Block

        """

        # Block is represented as a dictionary
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        # Add the newly created Block to the Blockchain
        self.chain.append(block)

        return block


    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        sender <str> -- Address of the Sender
        recipient <str> -- Address of the Recipient
        amount <int> -- Amount

        return <int> -- The index of the Block that will hold this transaction

        """

        # Transaction is represented as a dictionary
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        }

        # Add the newly created Transaction to the list of transactions
        self.current_transactions.append(transaction)

        return self.last_block['index'] + 1


    @property
    def last_block(self):
        """ Return the last Block in the Blockchain """

        return self.chain[-1]


    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        block <dict> -- Block

        return <str> -- Hash of the passed Block

        """

        # We must make sure that the Dictionary is ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()


    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof

        last_proof <int> -- The previous Block's proof

        return <int> -- The new Block's proof

        """

        # We do not know what the new Block's proof is yet
        proof = 0

        # Try every positive integer until we know the new Block's proof
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof


    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?

        last_proof <int> -- The previous Block's proof
        proof <int> -- The new Block's proof

        return <bool> True if correct, False if not

        """

        # Construct the function we are going to hash
        guess = f'{last_proof}{proof}'.encode()

        # Hash the function
        guess_hash = hashlib.sha256(guess).hexdigest()

        return guess_hash[:4] == "0000"


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        chain <list> -- the given blockchain

        return <bool> -- whether the given blockchain is valid or not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n----------\n")

            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False


    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        return <bool> -- True if our chain was replaces, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length if longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False
