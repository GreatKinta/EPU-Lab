// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @notice Local attestation ledger. Stock and personal data remain off-chain.
contract EquipmentLoan {
    address public immutable writer;
    struct Record { bytes32 loanRef; bytes32 dataHash; uint64 timestamp; uint8 kind; }
    mapping(bytes32 => Record) private records;
    mapping(bytes32 => bool) public borrowed;
    mapping(bytes32 => bool) public returned;
    event BorrowRecorded(bytes32 indexed operationId, bytes32 indexed loanRef, bytes32 dataHash, uint256 blockTimestamp);
    event ReturnRecorded(bytes32 indexed operationId, bytes32 indexed loanRef, bytes32 dataHash, uint256 blockTimestamp);
    constructor(address writer_) { require(writer_ != address(0), "zero writer"); writer = writer_; }
    modifier onlyWriter() { require(msg.sender == writer, "unauthorized"); _; }
    function recordBorrow(bytes32 operationId, bytes32 loanRef, bytes32 dataHash) external onlyWriter {
        require(!borrowed[loanRef], "already borrowed");
        _record(operationId, loanRef, dataHash, 1);
        borrowed[loanRef] = true;
        emit BorrowRecorded(operationId, loanRef, dataHash, block.timestamp);
    }
    function recordReturn(bytes32 operationId, bytes32 loanRef, bytes32 dataHash) external onlyWriter {
        require(borrowed[loanRef], "borrow missing");
        require(!returned[loanRef], "already returned");
        _record(operationId, loanRef, dataHash, 2);
        returned[loanRef] = true;
        emit ReturnRecorded(operationId, loanRef, dataHash, block.timestamp);
    }
    function _record(bytes32 operationId, bytes32 loanRef, bytes32 dataHash, uint8 kind) private {
        require(operationId != bytes32(0) && loanRef != bytes32(0) && dataHash != bytes32(0), "zero hash");
        require(records[operationId].kind == 0, "duplicate operation");
        records[operationId] = Record(loanRef, dataHash, uint64(block.timestamp), kind);
    }
    function getRecord(bytes32 operationId) external view returns (Record memory) { return records[operationId]; }
}
