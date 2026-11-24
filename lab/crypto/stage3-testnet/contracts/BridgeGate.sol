// SPDX-License-Identifier: MIT
// testnet בלבד. השער מ"קרדיט עיר" (offchain) ל-ESH. כבוי כברירת מחדל.
// זרימה: שרת העיר חותם voucher (EIP-712) → המשתמש מגיש → השער משחרר ESH מהיתרה שהאוצר הפקיד.
pragma solidity 0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

contract BridgeGate is Ownable, Pausable, ReentrancyGuard, EIP712 {
    using SafeERC20 for IERC20;

    IERC20 public immutable token;
    address public signer;              // מפתח השרת (testnet). לעולם לא סוכן.
    address public guardian;
    bool public enabled;                // המתג. false עד אישור עו"ד + אריאל.

    uint256 public perUserDailyCap;
    uint256 public globalDailyCap;
    mapping(address => bool) public kycAllowed;
    mapping(address => mapping(uint256 => bool)) public usedNonce;
    // חלון מתגלגל של 24 שעות: 24 דליים שעתיים (מונע "תקרה כפולה" סביב חצות)
    struct Window { uint64[24] hourOf; uint256[24] amount; }
    mapping(address => Window) private userWin;
    Window private globalWin;

    bytes32 private constant CLAIM_TYPEHASH =
        keccak256("Claim(address user,uint256 amount,uint256 nonce,uint256 deadline)");

    event Enabled(bool on);
    event Claimed(address indexed user, uint256 amount, uint256 nonce);
    event SignerChanged(address signer);
    event CapsChanged(uint256 perUser, uint256 global);
    event KycSet(address indexed user, bool allowed);

    error GateDisabled();
    error NotKyc();
    error Expired();
    error NonceUsed();
    error BadSignature();
    error UserCapExceeded();
    error GlobalCapExceeded();
    error NotGuardian();

    constructor(IERC20 token_, address owner_, address signer_, address guardian_, uint256 perUserCap, uint256 globalCap)
        Ownable(owner_)
        EIP712("EshBridgeGate", "1")
    {
        require(signer_ != address(0) && guardian_ != address(0), "zero addr");
        token = token_;
        signer = signer_;
        guardian = guardian_;
        perUserDailyCap = perUserCap;
        globalDailyCap = globalCap;
    }

    // ---- ניהול (multisig בלבד) ----
    function setEnabled(bool on) external onlyOwner { enabled = on; emit Enabled(on); }
    function setSigner(address s) external onlyOwner { require(s != address(0), "zero"); signer = s; emit SignerChanged(s); }
    function setCaps(uint256 perUser, uint256 global) external onlyOwner {
        perUserDailyCap = perUser; globalDailyCap = global; emit CapsChanged(perUser, global);
    }
    function setKyc(address user, bool allowed) external onlyOwner { kycAllowed[user] = allowed; emit KycSet(user, allowed); }
    function unpause() external onlyOwner { _unpause(); }
    /// מחזיר יתרה לאוצר (למשל לפני כיבוי סופי)
    function sweep(address to, uint256 amount) external onlyOwner { token.safeTransfer(to, amount); }

    // ---- מתג חירום ----
    function pause() external {
        if (msg.sender != guardian && msg.sender != owner()) revert NotGuardian();
        _pause();
    }

    // ---- משיכה ----
    function claim(uint256 amount, uint256 nonce, uint256 deadline, bytes calldata sig)
        external
        nonReentrant
        whenNotPaused
    {
        if (!enabled) revert GateDisabled();
        if (!kycAllowed[msg.sender]) revert NotKyc();
        if (block.timestamp > deadline) revert Expired();
        if (usedNonce[msg.sender][nonce]) revert NonceUsed();

        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(CLAIM_TYPEHASH, msg.sender, amount, nonce, deadline)));
        (address rec, ECDSA.RecoverError err,) = ECDSA.tryRecover(digest, sig);
        if (err != ECDSA.RecoverError.NoError || rec != signer) revert BadSignature();

        uint64 hour = uint64(block.timestamp / 1 hours);
        if (_windowSum(userWin[msg.sender], hour) + amount > perUserDailyCap) revert UserCapExceeded();
        if (_windowSum(globalWin, hour) + amount > globalDailyCap) revert GlobalCapExceeded();

        // effects לפני interactions
        usedNonce[msg.sender][nonce] = true;
        _windowAdd(userWin[msg.sender], hour, amount);
        _windowAdd(globalWin, hour, amount);

        token.safeTransfer(msg.sender, amount);
        emit Claimed(msg.sender, amount, nonce);
    }

    function _windowSum(Window storage w, uint64 hour) private view returns (uint256 sum) {
        for (uint256 i = 0; i < 24; i++) {
            if (w.hourOf[i] + 24 > hour) sum += w.amount[i]; // דלי מ-24 השעות האחרונות
        }
    }

    function _windowAdd(Window storage w, uint64 hour, uint256 amount) private {
        uint256 i = hour % 24;
        if (w.hourOf[i] != hour) { w.hourOf[i] = hour; w.amount[i] = 0; }
        w.amount[i] += amount;
    }

    function usedLast24h(address user) external view returns (uint256) {
        return _windowSum(userWin[user], uint64(block.timestamp / 1 hours));
    }

    function globalUsedLast24h() external view returns (uint256) {
        return _windowSum(globalWin, uint64(block.timestamp / 1 hours));
    }

    function domainSeparator() external view returns (bytes32) { return _domainSeparatorV4(); }
}
