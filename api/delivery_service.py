import os
import json
import logging
import re
from typing import Dict, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# Constants
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "delivery_matrix_cache.json")
SHOP_LOCATION = "Latha (Downtown)"

# Fallback Rule Engine Lookup Table
# Matches township names (case-insensitive) to rate and timeline
FALLBACK_RULES = {
    "latha": {"rate": 2000, "estimated_transit_timeline": "1 Day"},
    "sanchaung": {"rate": 2500, "estimated_transit_timeline": "1-2 Days"},
    "bahan": {"rate": 2500, "estimated_transit_timeline": "1-2 Days"},
    "kamayut": {"rate": 3000, "estimated_transit_timeline": "1-2 Days"},
    "yankin": {"rate": 3000, "estimated_transit_timeline": "1-2 Days"},
    "hlaing": {"rate": 3000, "estimated_transit_timeline": "1-2 Days"},
    "mayangone": {"rate": 3500, "estimated_transit_timeline": "2 Days"},
}

class DeliveryCalculationService:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.load_cache()

    def load_cache(self):
        """Loads cached shipping calculations from the JSON file."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached delivery calculations from {CACHE_FILE}")
            except Exception as e:
                logger.error(f"Error loading delivery matrix cache: {e}")

    def save_cache(self):
        """Persists the cache map back to the JSON file."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving delivery matrix cache: {e}")

    def _calculate_fallback(self, township_name: str) -> Dict[str, Any]:
        """Local Python fallback logic based on the lookup table."""
        name_lower = township_name.strip().lower()
        
        # Check against exact rule patterns
        for key, value in FALLBACK_RULES.items():
            if key in name_lower:
                return value
        
        # Default fallback for any other township
        return {"rate": 4500, "estimated_transit_timeline": "2-3 Days"}

    async def calculate_rate_and_timeline(self, township_name: str, region: str = "", division: str = "") -> Dict[str, Any]:
        """
        Calculates shipping rate and estimated transit timeline relative to the shop location (Latha).
        Uses Gemini AI with local fallback and JSON caching.
        """
        cache_key = f"{township_name}|{region}|{division}".strip().lower()
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Prepare fallback value
        fallback_val = self._calculate_fallback(township_name)

        # Check if Gemini is configured and available
        api_key = os.getenv("GEMINI_API_KEY", "")
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite").strip().lower().replace(" ", "-")

        if not api_key or not genai:
            logger.info(f"Gemini API not configured, using fallback for {township_name}")
            self.cache[cache_key] = fallback_val
            self.save_cache()
            return fallback_val

        try:
            # We construct a system prompt instructing Gemini how to compute rates and timelines
            # with Latha as the shop location.
            system_instruction = (
                f"You are a logistics and shipping cost calculator for an e-commerce shop in Myanmar.\n"
                f"The shop is located at: {SHOP_LOCATION}.\n\n"
                f"Here is the business rule rate and timeline matrix:\n"
                f"- Latha (Downtown) -> 2000 MMK, \"1 Day\"\n"
                f"- Sanchaung, Bahan -> 2500 MMK, \"1-2 Days\"\n"
                f"- Kamayut, Yankin, Hlaing -> 3000 MMK, \"1-2 Days\"\n"
                f"- Mayangone -> 3500 MMK, \"2 Days\"\n"
                f"- Any other township / fallback -> 4500 MMK, \"2-3 Days\"\n\n"
                f"Instructions:\n"
                f"1. You must calculate the shipping rate (MMK) and estimated transit timeline from the shop to the target township.\n"
                f"2. If the destination township matches one of the specific rules above, you MUST return that exact rate and timeline.\n"
                f"3. If the township is in Yangon but not listed, or if it is outside Yangon (e.g. other regions like Magway, Mandalay, etc.), you can estimate a reasonable rate and timeline (for example: higher rates like 5000-10000 MMK and timelines like 3-5 days for very remote areas, or stick to the fallback 4500 MMK and \"2-3 Days\" if appropriate). Keep rates in increments of 500 MMK.\n"
                f"4. You MUST respond with a JSON object in this format:\n"
                f"{{\n"
                f"  \"rate\": <integer>,\n"
                f"  \"estimated_transit_timeline\": \"<string>\"\n"
                f"}}\n"
            )

            prompt = (
                f"Calculate shipping from '{SHOP_LOCATION}' to:\n"
                f"Township Name: {township_name}\n"
                f"Division/District: {division}\n"
                f"Region: {region}"
            )

            # Reconfigure API key in case it wasn't configured earlier
            genai.configure(api_key=api_key)
            
            # Use structured json response
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Non-blocking async API call
            response = await model.generate_content_async(prompt)
            result_text = response.text.strip()
            
            # Parse the JSON response safely
            data = json.loads(result_text)
            rate = int(data.get("rate", fallback_val["rate"]))
            timeline = str(data.get("estimated_transit_timeline", fallback_val["estimated_transit_timeline"]))
            
            computed_val = {
                "rate": rate,
                "estimated_transit_timeline": timeline
            }
            
            self.cache[cache_key] = computed_val
            self.save_cache()
            return computed_val

        except Exception as e:
            logger.error(f"Error calculating rate using Gemini for {township_name}: {e}. Using fallback.", exc_info=True)
            # Safe fallback integration
            self.cache[cache_key] = fallback_val
            self.save_cache()
            return fallback_val

# Global singleton service
delivery_service = DeliveryCalculationService()
