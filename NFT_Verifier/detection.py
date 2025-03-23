from datetime import datetime, timedelta

def analyze_nft_risk(nft_data, transaction_history, known_scammers):
    risk_score = 0
    risk_factors = []

    if nft_data['owner'] in known_scammers:
        risk_score += 100
        risk_factors.append("OWNER_IS_KNOWN_SCAMMER")

    transfer_count = sum(1 for tx in transaction_history if 'transfer' in tx['type'])
    if transfer_count > 3:
        risk_score += 20 * (transfer_count - 3)
        risk_factors.append("HIGH_TRANSFER_VELOCITY")

    if datetime.fromisoformat(nft_data['created_at']) > datetime.now() - timedelta(days=30):
        risk_score += 15
        risk_factors.append("NEW_ACCOUNT")

    return {
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "is_high_risk": risk_score >= 70
    }

def verify_nft_metadata(nft_data):
    expected_fields = {"name", "image", "description"}
    return all(field in nft_data for field in expected_fields)
