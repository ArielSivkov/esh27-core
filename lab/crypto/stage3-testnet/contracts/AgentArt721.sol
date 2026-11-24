// SPDX-License-Identifier: MIT
// testnet בלבד. יצירות של סוכני העיר. תמלוגי יוצר ERC-2981 (לא חלוקת רווחים למחזיקים).
pragma solidity 0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721URIStorage} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract AgentArt721 is ERC721URIStorage, ERC2981, Ownable {
    uint256 public nextId = 1;
    uint96 public constant MAX_ROYALTY_BPS = 1000; // 10% מקסימום
    mapping(uint256 => bytes32) public agentOf; // מזהה הסוכן שיצר

    constructor(address owner_, address royaltyReceiver, uint96 bps)
        ERC721("Ashdod Agent Art (TESTNET)", "tART")
        Ownable(owner_)
    {
        require(bps <= MAX_ROYALTY_BPS, "royalty too high");
        _setDefaultRoyalty(royaltyReceiver, bps);
    }

    /// הסוכן רק מציע; ה-owner (אדם/multisig) מנפיק.
    function mintArt(address to, bytes32 agentId, string calldata uri) external onlyOwner returns (uint256 id) {
        id = nextId++;
        _safeMint(to, id);
        _setTokenURI(id, uri);
        agentOf[id] = agentId;
    }

    function supportsInterface(bytes4 i) public view override(ERC721URIStorage, ERC2981) returns (bool) {
        return super.supportsInterface(i);
    }
}
