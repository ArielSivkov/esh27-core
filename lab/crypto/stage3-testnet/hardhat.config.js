// testnet בלבד. אין כאן מפתחות. אין רשת mainnet בקונפיג — בכוונה.
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-chai-matchers");
const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");
const path = require("path");

// הסביבה חוסמת הורדת קומפיילר; משתמשים ב-solcjs מקומי מ-npm.
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD, async (args, hre, runSuper) => {
  if (args.solcVersion === "0.8.24") {
    return {
      compilerPath: path.join(__dirname, "node_modules", "solc", "soljson.js"),
      isSolcJs: true,
      version: args.solcVersion,
      longVersion: require("solc/package.json").version,
    };
  }
  return runSuper();
});

const networks = { hardhat: {} };
// Base Sepolia רק אם הוגדר מפתח בסביבה (לעולם לא בקוד). chainId נעול ל-84532.
if (process.env.TESTNET_DEPLOYER_KEY) {
  networks.baseSepolia = {
    url: process.env.BASE_SEPOLIA_RPC || "https://sepolia.base.org",
    chainId: 84532,
    accounts: [process.env.TESTNET_DEPLOYER_KEY],
  };
}

module.exports = {
  solidity: { version: "0.8.24", settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: "cancun" } },
  networks,
};
