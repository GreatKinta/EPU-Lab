import { createRequire } from 'node:module';
import { defineConfig } from 'hardhat/config';
import hardhatEthers from '@nomicfoundation/hardhat-ethers';
import hardhatMocha from '@nomicfoundation/hardhat-mocha';
export default defineConfig({ plugins: [hardhatEthers, hardhatMocha], solidity: { version: '0.8.28', path: createRequire(import.meta.url).resolve('solc/soljson.js') }, networks: { localhost: { type: 'http', url: process.env.RPC_URL || 'http://127.0.0.1:8545', chainId: 31337 } } });
