import os
import csv
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query
from api.delivery_service import delivery_service

logger = logging.getLogger(__name__)

router = APIRouter()

# CSV file path relative to this file
CSV_FILE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "myanmar-townships.csv"
    )
)

# 12 Mock Township rows for seamless initial load
MOCK_TOWNSHIPS = [
    { "id": "ts_1", "township_name": "Kamayut", "region": "Yangon Region", "division": "Yangon West" },
    { "id": "ts_2", "township_name": "Sanchaung", "region": "Yangon Region", "division": "Yangon West" },
    { "id": "ts_3", "township_name": "Latha (Downtown)", "region": "Yangon Region", "division": "Yangon West" },
    { "id": "ts_4", "township_name": "Yankin", "region": "Yangon Region", "division": "Yangon East" },
    { "id": "ts_5", "township_name": "Bahan", "region": "Yangon Region", "division": "Yangon West" },
    { "id": "ts_6", "township_name": "Mayangone", "region": "Yangon Region", "division": "Yangon North" },
    { "id": "ts_7", "township_name": "Hlaing", "region": "Yangon Region", "division": "Yangon West" },
    { "id": "ts_8", "township_name": "Tamwe", "region": "Yangon Region", "division": "Yangon East" },
    { "id": "ts_9", "township_name": "Thingangyun", "region": "Yangon Region", "division": "Yangon East" },
    { "id": "ts_10", "township_name": "Insein", "region": "Yangon Region", "division": "Yangon North" },
    { "id": "ts_11", "township_name": "North Dagon", "region": "Yangon Region", "division": "Yangon East" },
    { "id": "ts_12", "township_name": "South Dagon", "region": "Yangon Region", "division": "Yangon East" }
]

def load_master_dataset() -> List[Dict[str, Any]]:
    """
    Loads and compiles the master dataset: 12 mock townships followed by
    townships parsed from the myanmar-townships.csv file.
    """
    dataset = list(MOCK_TOWNSHIPS)
    
    if os.path.exists(CSV_FILE_PATH):
        try:
            with open(CSV_FILE_PATH, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                
                for idx, row in enumerate(reader):
                    # Strip whitespace from keys and values to avoid header space mismatch issues
                    clean_row = {k.strip(): v.strip() for k, v in row.items() if k is not None and v is not None}
                    region = clean_row.get("Region", "")
                    division = clean_row.get("Division", "")
                    township = clean_row.get("Township", "")
                    
                    if not township:
                        continue
                        
                    dataset.append({
                        "id": f"csv_{idx + 1}",
                        "township_name": township,
                        "region": region,
                        "division": division
                    })
            logger.info(f"Successfully loaded master dataset with {len(dataset)} items ({len(MOCK_TOWNSHIPS)} mock + {len(dataset) - len(MOCK_TOWNSHIPS)} CSV).")
        except Exception as e:
            logger.error(f"Error parsing CSV dataset at {CSV_FILE_PATH}: {e}")
    else:
        logger.warning(f"CSV dataset not found at {CSV_FILE_PATH}. Using mock townships only.")
        
    return dataset

# Initialize master dataset at startup
MASTER_DATASET = load_master_dataset()

@router.get("/delivery-matrix")
async def get_delivery_matrix(
    page: int = Query(default=1, ge=1, description="The target page index"),
    limit: int = Query(default=10, ge=1, le=100, description="Max records returned per request"),
    search: Optional[str] = Query(default=None, description="Sub-string filtering case-insensitive against township_name")
):
    """
    GET /api/v1/delivery-matrix
    Serves a paginated and searchable list of Myanmar townships with their calculated shipping rates and transit timelines.
    """
    # 1. Filter dataset by search term
    filtered_data = MASTER_DATASET
    if search:
        search_term = search.strip().lower()
        filtered_data = [
            item for item in MASTER_DATASET
            if search_term in item["township_name"].lower()
        ]

    # 2. Strict Pagination Calculations
    total_records = len(filtered_data)
    total_pages = (total_records + limit - 1) // limit if total_records > 0 else 1

    # Adjust page bounds
    current_page = page
    if current_page > total_pages:
        current_page = total_pages
    if current_page < 1:
        current_page = 1

    start_idx = (current_page - 1) * limit
    end_idx = start_idx + limit
    paginated_items = filtered_data[start_idx:end_idx]

    # 3. Dynamic Rate and Timeline calculation (AI-driven with cache & local fallback)
    result_data = []
    for item in paginated_items:
        calc_result = await delivery_service.calculate_rate_and_timeline(
            township_name=item["township_name"],
            region=item.get("region", ""),
            division=item.get("division", "")
        )
        
        result_data.append({
            "id": item["id"],
            "township_name": item["township_name"],
            "region": item["region"],
            "division": item["division"],
            "rate": calc_result["rate"],
            "estimated_transit_timeline": calc_result["estimated_transit_timeline"]
        })

    # 4. Paginated JSON Payload construction
    return {
        "data": result_data,
        "pagination": {
            "total_records": total_records,
            "current_page": current_page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1
        }
    }
