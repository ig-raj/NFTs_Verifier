# app.py (updated)
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
from typing import Optional
from nft_verifier import NFTVerifier

app = FastAPI()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# Initialize verifier
nft_verifier = NFTVerifier()

@app.get("/verify/owner/{owner_address}")
async def verify_by_owner(owner_address: str):
    """Verify NFTs owned by a specific address."""
    try:
        logger.info(f"Verifying NFTs for Owner: {owner_address}")
        verification_result = nft_verifier.get_nft_data_by_owner(owner_address)
        
        if not verification_result.get("nfts"):
            raise HTTPException(status_code=404, detail="No NFTs found for this owner")
            
        return verification_result
    except HTTPException as e:
        logger.error(f"HTTP Error: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/verify/collection")
async def verify_by_collection(
    creator_address: str,
    collection_name: str,
    token_id: Optional[str] = Query(None)
):
    """Verify a collection by creator address and collection name, optionally filtering by token ID."""
    try:
        logger.info(f"Verifying Collection: {collection_name} by Creator: {creator_address}, Token ID: {token_id}")
        verification_result = nft_verifier.get_nft_data_by_collection(
            creator_address, collection_name, token_id
        )
        
        if not verification_result.get("collection_data"):
            raise HTTPException(status_code=404, detail="Collection not found")
            
        return verification_result
    except HTTPException as e:
        logger.error(f"HTTP Error: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/verify/nft")
async def verify_single_nft(
    owner_address: Optional[str] = Query(None),
    creator_address: Optional[str] = Query(None),
    collection_name: Optional[str] = Query(None),
    token_id: Optional[str] = Query(None)
):
    """Verify a single NFT using any combination of identifiers."""
    try:
        logger.info(f"Verifying NFT: Owner={owner_address}, Creator={creator_address}, Collection={collection_name}, TokenID={token_id}")
        
        # Implementation depends on which parameters are provided
        if owner_address:
            result = nft_verifier.get_nft_data_by_owner(owner_address)
            if token_id and result.get("nfts"):
                # Filter to specific token if token_id is provided
                result["nfts"] = [nft for nft in result["nfts"] if str(nft.get("id")) == token_id]
            return result
            
        elif creator_address and collection_name:
            return nft_verifier.get_nft_data_by_collection(creator_address, collection_name)
            
        else:
            raise HTTPException(
                status_code=400, 
                detail="Insufficient parameters. Provide either owner_address or (creator_address AND collection_name)"
            )
    
    except HTTPException as e:
        logger.error(f"HTTP Error: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")