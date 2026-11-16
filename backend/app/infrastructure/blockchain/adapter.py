import json

from web3 import Web3
from web3.exceptions import TransactionNotFound

from app.core.config import get_settings


class ChainAdapter:
    def __init__(self):
        settings = get_settings()
        config = (
            json.loads(settings.chain_config_path.read_text())
            if settings.chain_config_path.exists()
            else {}
        )
        self.web3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 10}))
        if settings.chain_id != 31337 or self.web3.eth.chain_id != settings.chain_id:
            raise RuntimeError("Only local chain 31337 is supported by this demo")
        address = settings.contract_address or config.get("address")
        if not address or not self.web3.eth.get_code(Web3.to_checksum_address(address)):
            raise RuntimeError("Deploy local contract before starting worker")
        abi = config.get("abi")
        if not abi:
            from pathlib import Path

            abi = json.loads(Path(__file__).with_name("EquipmentLoan.abi.json").read_text())
        self.contract = self.web3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
        self.private_key = settings.relayer_private_key or config.get("relayer_private_key")

    def read(self, operation):
        result = self.contract.functions.getRecord(operation).call()
        return {
            "loan_ref": Web3.to_hex(result[0]),
            "data_hash": Web3.to_hex(result[1]),
            "timestamp": result[2],
            "kind": result[3],
        }

    def sign(self, event, transaction):
        if not self.private_key:
            raise RuntimeError("Relayer signing key is not configured")
        account = self.web3.eth.account.from_key(self.private_key)
        if account.address != self.contract.functions.writer().call():
            raise RuntimeError("Relayer is not the authorized writer")
        nonce = self.web3.eth.get_transaction_count(account.address, "pending")
        method = (
            self.contract.functions.recordBorrow
            if event.event_type == "BorrowApproved"
            else self.contract.functions.recordReturn
        )
        data = method(
            transaction.operation_id, event.payload["loan_ref"], transaction.data_hash
        ).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "chainId": 31337,
                "gas": 300000,
                "gasPrice": self.web3.eth.gas_price,
            }
        )
        signed = account.sign_transaction(data)
        return nonce, Web3.to_hex(signed.raw_transaction), Web3.to_hex(signed.hash)

    def broadcast(self, raw):
        return Web3.to_hex(self.web3.eth.send_raw_transaction(raw))

    def receipt(self, tx_hash):
        try:
            return self.web3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            return None
