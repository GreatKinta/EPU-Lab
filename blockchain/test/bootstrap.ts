import { describe, it } from 'mocha';
import assert from 'node:assert/strict';
import { network } from 'hardhat';
describe('Bootstrap', () => {
  it('deploys EquipmentLoan with the configured writer', async () => {
    const { ethers } = await network.create();
    const [writer] = await ethers.getSigners();
    const contract = await ethers.deployContract('EquipmentLoan', [writer.address]);
    assert.equal(await contract.writer(), writer.address);
  });
});
