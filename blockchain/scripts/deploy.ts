import { network } from 'hardhat';
import { Wallet } from 'ethers';
import { mkdir, readFile, writeFile, rename } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
const { ethers } = await network.create();
const chain = await ethers.provider.getNetwork();
if(chain.chainId !== 31337n) throw new Error('Deploy is restricted to the local Hardhat chain 31337');
const target=process.env.CHAIN_CONFIG_PATH || resolve('../runtime/local.json');
let existing:any;
try {existing=JSON.parse(await readFile(target,'utf8'));} catch {}
if(existing && await ethers.provider.getCode(existing.address)!=='0x') {
 const current=await ethers.getContractAt('EquipmentLoan',existing.address);
 const wallet=new Wallet(existing.relayer_private_key);
 if(await current.writer()!==wallet.address) throw new Error('Existing config writer mismatch');
 console.log('Local deployment already exists at',existing.address);
} else {
 const [deployer]=await ethers.getSigners();const wallet=Wallet.createRandom();
 await(await deployer.sendTransaction({to:wallet.address,value:ethers.parseEther('100')})).wait();
 const contract=await ethers.deployContract('EquipmentLoan',[wallet.address]);await contract.waitForDeployment();
 const config={chain_id:31337,address:await contract.getAddress(),abi:JSON.parse(contract.interface.formatJson()),relayer_private_key:wallet.privateKey};
 await mkdir(dirname(target),{recursive:true});await writeFile(`${target}.tmp`,JSON.stringify(config,null,2),{mode:0o600});await rename(`${target}.tmp`,target);
 console.log('Local contract deployed at',config.address,'(private runtime config generated)');
}
