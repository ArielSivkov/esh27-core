// SPDX-License-Identifier: MIT
// testnet בלבד. "אש" (ESH) — טוקן העיר. היצע קבוע, אין mint אחרי הפריסה.
pragma solidity 0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Burnable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import {ERC20Pausable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

contract CityToken is ERC20, ERC20Burnable, ERC20Pausable, AccessControl {
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    uint256 public constant MAX_SUPPLY = 1_000_000_000 ether;

    /// @param treasury ה-multisig שמקבל את כל ההיצע ומחזיק את ה-admin
    /// @param guardian מי שיכול להפעיל מתג חירום (pause) — אדם, לא סוכן
    constructor(address treasury, address guardian) ERC20("Esh City Token (TESTNET)", "tESH") {
        require(treasury != address(0) && guardian != address(0), "zero addr");
        _mint(treasury, MAX_SUPPLY);
        _grantRole(DEFAULT_ADMIN_ROLE, treasury);
        _grantRole(PAUSER_ROLE, guardian);
        _grantRole(PAUSER_ROLE, treasury);
    }

    function pause() external onlyRole(PAUSER_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }

    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Pausable) {
        super._update(from, to, value);
    }
}
