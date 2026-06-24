"""
swarm/tools/companies_house.py
Simulated UK Companies House API client.
Provides free, structured accounts for UK entities (PLCs and Ltds) without API credentials.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("swarm.tools.companies_house")

# Curated financial data for key UK target corporations
UK_COMPANIES_DATABASE = {
    # Barclays Holdings Ltd (Private/Holdco)
    "barclays": {
        "company_number": "01234567",
        "company_name": "BARCLAYS HOLDINGS LTD",
        "company_status": "active",
        "jurisdiction": "united-kingdom",
        "company_type": "ltd",
        "latest_accounts": {
            "period": "2024-12-31",
            "currency": "GBP",
            "latest_revenue": 18200000000.0,
            "latest_debt_to_equity": 1.58,
            "industry_avg_debt_equity": 1.20,
            "ebitda_margin": 0.22,
            "net_income": 4000000000.0,
            "total_liabilities": 25000000000.0,
            "total_equity": 15800000000.0,
            "interest_coverage_ratio": 8.5,
            "cash_runway_months": "Infinite (Positive Cash Flow)"
        }
    },
    # BP UK Ltd
    "bp": {
        "company_number": "02345678",
        "company_name": "BP UK RETAIL LTD",
        "company_status": "active",
        "jurisdiction": "united-kingdom",
        "company_type": "ltd",
        "latest_accounts": {
            "period": "2024-12-31",
            "currency": "GBP",
            "latest_revenue": 56000000.0,
            "latest_debt_to_equity": 0.95,
            "industry_avg_debt_equity": 1.10,
            "ebitda_margin": 0.12,
            "net_income": 6720000.0,
            "total_liabilities": 22000000.0,
            "total_equity": 23150000.0,
            "interest_coverage_ratio": 12.4,
            "cash_runway_months": "Infinite (Positive Cash Flow)"
        }
    },
    # Acme UK Ltd
    "acme": {
        "company_number": "09876543",
        "company_name": "ACME DILIGENCE UK LTD",
        "company_status": "active",
        "jurisdiction": "united-kingdom",
        "company_type": "ltd",
        "latest_accounts": {
            "period": "2024-12-31",
            "currency": "GBP",
            "latest_revenue": 4500000.0,
            "latest_debt_to_equity": 2.25, # High leverage!
            "industry_avg_debt_equity": 1.10,
            "ebitda_margin": -0.05, # Negative EBITDA!
            "net_income": -225000.0,
            "total_liabilities": 1800000.0,
            "total_equity": 800000.0,
            "interest_coverage_ratio": -0.5,
            "cash_runway_months": 8.0 # Critical Cash Runway!
        }
    }
}

def get_companies_house_accounts(company_name: str) -> Optional[Dict[str, Any]]:
    """
    Simulates querying the UK Companies House REST API for audited financial statements.
    """
    clean_name = company_name.strip().lower()
    
    # Check for direct key match
    for key, data in UK_COMPANIES_DATABASE.items():
        if key in clean_name:
            logger.info(f"Companies House Hit: Resolved '{company_name}' to '{data['company_name']}'")
            return data
            
    # Generate stable mock if no match found
    logger.info(f"Companies House Lookup: Generating simulated records for private UK entity '{company_name}'")
    h = hash(clean_name)
    company_num = f"0{abs(h) % 90000000 + 10000000:07d}"
    
    latest_rev = float(2500000 + (h % 5000000))
    liabilities = float(1000000 + (h % 2000000))
    equity = float(1200000 + ((h * 2) % 3000000))
    d_e = liabilities / equity if equity > 0 else 1.0
    net_inc = latest_rev * (0.05 + (h % 10) / 100.0)
    
    return {
        "company_number": company_num,
        "company_name": f"{company_name.upper()} LTD",
        "company_status": "active",
        "jurisdiction": "united-kingdom",
        "company_type": "ltd",
        "latest_accounts": {
            "period": "2024-12-31",
            "currency": "GBP",
            "latest_revenue": latest_rev,
            "latest_debt_to_equity": round(d_e, 3),
            "industry_avg_debt_equity": 1.10,
            "ebitda_margin": round(0.08 + (h % 15) / 100.0, 4),
            "net_income": net_inc,
            "total_liabilities": liabilities,
            "total_equity": equity,
            "interest_coverage_ratio": round(4.5 + (h % 15) / 2.0, 2),
            "cash_runway_months": "Infinite (Positive Cash Flow)" if net_inc > 0 else round(12.0 + (h % 12), 1)
        }
    }
