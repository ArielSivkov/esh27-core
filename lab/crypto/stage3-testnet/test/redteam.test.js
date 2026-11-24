// בדיקות + צוות אדום. רשת מקומית של hardhat בלבד.
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

const E = (n) => ethers.parseEther(String(n));

async function deploy() {
  const [treasury, guardian, signer, alice, bob, mallory] = await ethers.getSigners();
  const token = await (await ethers.getContractFactory("CityToken")).deploy(treasury.address, guardian.address);
  const gate = await (await ethers.getContractFactory("BridgeGate")).deploy(
    await token.getAddress(), treasury.address, signer.address, guardian.address, E(1000), E(10000)
  );
  await token.connect(treasury).transfer(await gate.getAddress(), E(1_000_000));
  return { token, gate, treasury, guardian, signer, alice, bob, mallory };
}

async function voucher(gate, signer, user, amount, nonce, deadline) {
  const net = await ethers.provider.getNetwork();
  const domain = { name: "EshBridgeGate", version: "1", chainId: net.chainId, verifyingContract: await gate.getAddress() };
  const types = { Claim: [
    { name: "user", type: "address" }, { name: "amount", type: "uint256" },
    { name: "nonce", type: "uint256" }, { name: "deadline", type: "uint256" },
  ] };
  return signer.signTypedData(domain, types, { user, amount, nonce, deadline });
}

async function ready(ctx) {
  await ctx.gate.connect(ctx.treasury).setEnabled(true);
  await ctx.gate.connect(ctx.treasury).setKyc(ctx.alice.address, true);
  return (await time.latest()) + 3600;
}

describe("CityToken (tESH)", () => {
  it("היצע קבוע: כל ההיצע לאוצר, ואין פונקציית mint", async () => {
    const { token, treasury } = await deploy();
    expect(await token.totalSupply()).to.equal(E(1_000_000_000));
    expect(token.mint).to.equal(undefined);
    expect(await token.balanceOf(treasury.address)).to.equal(E(999_000_000));
  });
  it("burn מקטין היצע", async () => {
    const { token, treasury } = await deploy();
    await token.connect(treasury).burn(E(5));
    expect(await token.totalSupply()).to.equal(E(999_999_995));
  });
  it("מתג חירום: guardian עוצר; רק האוצר מחזיר", async () => {
    const { token, treasury, guardian, alice } = await deploy();
    await token.connect(guardian).pause();
    await expect(token.connect(treasury).transfer(alice.address, 1)).to.be.revertedWithCustomError(token, "EnforcedPause");
    await expect(token.connect(guardian).unpause()).to.be.revertedWithCustomError(token, "AccessControlUnauthorizedAccount");
    await token.connect(treasury).unpause();
    await token.connect(treasury).transfer(alice.address, 1);
  });
  it("צוות אדום: זר לא יכול לעצור או לקבל הרשאות", async () => {
    const { token, mallory } = await deploy();
    await expect(token.connect(mallory).pause()).to.be.reverted;
    const ADMIN = await token.DEFAULT_ADMIN_ROLE();
    await expect(token.connect(mallory).grantRole(ADMIN, mallory.address)).to.be.reverted;
  });
});

describe("BridgeGate", () => {
  it("כבוי כברירת מחדל", async () => {
    const ctx = await deploy();
    const dl = (await time.latest()) + 3600;
    await ctx.gate.connect(ctx.treasury).setKyc(ctx.alice.address, true);
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "GateDisabled");
  });
  it("משיכה תקינה", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig);
    expect(await ctx.token.balanceOf(ctx.alice.address)).to.equal(E(10));
  });
  it("צוות אדום: replay של אותו voucher נחסם", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "NonceUsed");
  });
  it("צוות אדום: גניבת voucher של אחר נכשלת", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    await ctx.gate.connect(ctx.treasury).setKyc(ctx.mallory.address, true);
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.mallory).claim(E(10), 1, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "BadSignature");
  });
  it("צוות אדום: חתימה של לא-signer, או סכום מנופח, נכשלת", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    const forged = await voucher(ctx.gate, ctx.mallory, ctx.alice.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, forged)).to.be.revertedWithCustomError(ctx.gate, "BadSignature");
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 2, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(999), 2, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "BadSignature");
  });
  it("צוות אדום: voucher לשער אחר (cross-contract replay) נכשל", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    const other = await (await ethers.getContractFactory("BridgeGate")).deploy(
      await ctx.token.getAddress(), ctx.treasury.address, ctx.signer.address, ctx.guardian.address, E(1000), E(10000));
    const sigForOther = await voucher(other, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sigForOther)).to.be.revertedWithCustomError(ctx.gate, "BadSignature");
  });
  it("פג תוקף", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await time.increaseTo(dl + 1);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "Expired");
  });
  it("בלי KYC — חסום", async () => {
    const ctx = await deploy(); await ready(ctx);
    const dl = (await time.latest()) + 3600;
    const sig = await voucher(ctx.gate, ctx.signer, ctx.bob.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.bob).claim(E(10), 1, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "NotKyc");
  });
  it("צוות אדום: תקרה יומית למשתמש, ואיפוס ביום הבא", async () => {
    const ctx = await deploy(); let dl = await ready(ctx);
    let sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(1000), 1, dl);
    await ctx.gate.connect(ctx.alice).claim(E(1000), 1, dl, sig);
    sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(1), 2, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(1), 2, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "UserCapExceeded");
    await time.increase(86400); dl = (await time.latest()) + 3600;
    sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(1), 3, dl);
    await ctx.gate.connect(ctx.alice).claim(E(1), 3, dl, sig);
  });
  it("צוות אדום: תקרה גלובלית מול הרבה ארנקי sybil", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    const wallets = (await ethers.getSigners()).slice(6, 17); // 11 ארנקים × 1000 > 10000
    let fails = 0;
    for (let i = 0; i < wallets.length; i++) {
      await ctx.gate.connect(ctx.treasury).setKyc(wallets[i].address, true);
      const sig = await voucher(ctx.gate, ctx.signer, wallets[i].address, E(1000), 1, dl);
      try { await ctx.gate.connect(wallets[i]).claim(E(1000), 1, dl, sig); } catch { fails++; }
    }
    expect(fails).to.equal(1);
    expect(await ctx.gate.globalUsedLast24h()).to.equal(E(10000));
  });
  it("צוות אדום: זר לא יכול להדליק שער, להחליף signer או לרוקן", async () => {
    const ctx = await deploy();
    await expect(ctx.gate.connect(ctx.mallory).setEnabled(true)).to.be.revertedWithCustomError(ctx.gate, "OwnableUnauthorizedAccount");
    await expect(ctx.gate.connect(ctx.mallory).setSigner(ctx.mallory.address)).to.be.revertedWithCustomError(ctx.gate, "OwnableUnauthorizedAccount");
    await expect(ctx.gate.connect(ctx.mallory).sweep(ctx.mallory.address, 1)).to.be.revertedWithCustomError(ctx.gate, "OwnableUnauthorizedAccount");
    await expect(ctx.gate.connect(ctx.mallory).setKyc(ctx.mallory.address, true)).to.be.revertedWithCustomError(ctx.gate, "OwnableUnauthorizedAccount");
    await expect(ctx.gate.connect(ctx.mallory).pause()).to.be.revertedWithCustomError(ctx.gate, "NotGuardian");
  });
  it("צוות אדום: אין תקרה כפולה סביב חצות (חלון מתגלגל)", async () => {
    const ctx = await deploy();
    const now = await time.latest();
    await time.increaseTo(Math.floor(now / 86400 + 1) * 86400 - 60); // 23:59
    let dl = await ready(ctx);
    let sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(1000), 1, dl);
    await ctx.gate.connect(ctx.alice).claim(E(1000), 1, dl, sig);
    await time.increase(120); // 00:01
    sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(1000), 2, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(1000), 2, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "UserCapExceeded");
    await time.increase(24 * 3600);
    dl = (await time.latest()) + 3600;
    sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(1000), 3, dl);
    await ctx.gate.connect(ctx.alice).claim(E(1000), 3, dl, sig);
  });
  it("Timelock: שינוי בשער רק אחרי 48 שעות; מתג חירום מיידי", async () => {
    const ctx = await deploy();
    const [, , , , , , safe] = await ethers.getSigners(); // מייצג Safe multisig
    const DELAY = 48 * 3600;
    const tl = await (await ethers.getContractFactory("TimelockController")).deploy(DELAY, [safe.address], [safe.address], ethers.ZeroAddress);
    await ctx.gate.connect(ctx.treasury).transferOwnership(await tl.getAddress());
    await expect(ctx.gate.connect(ctx.treasury).setEnabled(true)).to.be.revertedWithCustomError(ctx.gate, "OwnableUnauthorizedAccount");
    const data = ctx.gate.interface.encodeFunctionData("setEnabled", [true]);
    const target = await ctx.gate.getAddress();
    const salt = ethers.id("enable-1");
    await expect(tl.connect(ctx.mallory).schedule(target, 0, data, ethers.ZeroHash, salt, DELAY)).to.be.reverted;
    await tl.connect(safe).schedule(target, 0, data, ethers.ZeroHash, salt, DELAY);
    await expect(tl.connect(safe).execute(target, 0, data, ethers.ZeroHash, salt)).to.be.reverted;
    await ctx.gate.connect(ctx.guardian).pause(); // חירום לא מחכה
    expect(await ctx.gate.paused()).to.equal(true);
    await time.increase(DELAY + 1);
    await tl.connect(safe).execute(target, 0, data, ethers.ZeroHash, salt);
    expect(await ctx.gate.enabled()).to.equal(true);
  });
  it("מתג חירום בשער", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    await ctx.gate.connect(ctx.guardian).pause();
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig)).to.be.revertedWithCustomError(ctx.gate, "EnforcedPause");
  });
  it("צוות אדום: מתג החירום של הטוקן עוצר גם את השער", async () => {
    const ctx = await deploy(); const dl = await ready(ctx);
    await ctx.token.connect(ctx.guardian).pause();
    const sig = await voucher(ctx.gate, ctx.signer, ctx.alice.address, E(10), 1, dl);
    await expect(ctx.gate.connect(ctx.alice).claim(E(10), 1, dl, sig)).to.be.reverted;
  });
});

describe("NFTs", () => {
  it("חלקה: גריד קבוע, בלי כפילויות, רק owner מנפיק", async () => {
    const [owner, alice, mallory] = await ethers.getSigners();
    const p = await (await ethers.getContractFactory("Parcel721")).deploy(owner.address, "ipfs://x/");
    await p.mintParcel(alice.address, 3, 4);
    expect(await p.ownerOf(403)).to.equal(alice.address);
    await expect(p.mintParcel(alice.address, 3, 4)).to.be.reverted;
    await expect(p.mintParcel(alice.address, 100, 0)).to.be.revertedWithCustomError(p, "OutOfGrid");
    await expect(p.connect(mallory).mintParcel(mallory.address, 0, 0)).to.be.revertedWithCustomError(p, "OwnableUnauthorizedAccount");
  });
  it("יצירה: תמלוג מוגבל ל-10%, ורק owner מנפיק", async () => {
    const [owner, alice, mallory] = await ethers.getSigners();
    const F = await ethers.getContractFactory("AgentArt721");
    await expect(F.deploy(owner.address, owner.address, 1001)).to.be.revertedWith("royalty too high");
    const a = await F.deploy(owner.address, owner.address, 500);
    await a.mintArt(alice.address, ethers.id("agent-7"), "ipfs://art/1");
    const [, amt] = await a.royaltyInfo(1, E(100));
    expect(amt).to.equal(E(5));
    await expect(a.connect(mallory).mintArt(mallory.address, ethers.ZeroHash, "x")).to.be.revertedWithCustomError(a, "OwnableUnauthorizedAccount");
  });
});
