// SPDX-License-Identifier: MIT
// testnet בלבד. חלקות באשדוד הווירטואלית — גריד קבוע, אין הכנסה/שכירות מובנית.
pragma solidity 0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract Parcel721 is ERC721, Ownable {
    uint256 public constant WIDTH = 100;
    uint256 public constant HEIGHT = 100;
    uint256 public constant MAX_PARCELS = WIDTH * HEIGHT; // 10,000, קבוע לתמיד
    uint256 public minted;
    string private baseURI_;

    error OutOfGrid();

    constructor(address owner_, string memory uri) ERC721("Ashdod Virtual Parcel (TESTNET)", "tPARCEL") Ownable(owner_) {
        baseURI_ = uri;
    }

    function parcelId(uint256 x, uint256 y) public pure returns (uint256) {
        if (x >= WIDTH || y >= HEIGHT) revert OutOfGrid();
        return y * WIDTH + x;
    }

    function mintParcel(address to, uint256 x, uint256 y) external onlyOwner returns (uint256 id) {
        id = parcelId(x, y);
        _safeMint(to, id); // מונע כפילות: ERC721 נכשל אם id קיים
        minted++;
    }

    function _baseURI() internal view override returns (string memory) { return baseURI_; }
}
