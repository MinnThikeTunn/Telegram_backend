import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

STATE_FILE = "sales_brain_state.json"

@dataclass
class UserProfile:
    user_id: str
    user_name: str = "Customer"
    likes: List[str] = field(default_factory=list)
    dislikes: List[str] = field(default_factory=list)
    order_history: List[Dict[str, Any]] = field(default_factory=list)
    predicted_interests: List[str] = field(default_factory=list)
    cart: List[Dict[str, Any]] = field(default_factory=list)
    current_step: str = "browsing"
    temp_pay_method: str = ""
    active_order_id: str = ""
    last_activity_ts: float = 0.0
    browsing_product_id: str = ""
    notify_when_available: List[str] = field(default_factory=list)
    wishlist: List[str] = field(default_factory=list)

class UserAnalyticsStore:
    def __init__(self, file_path: str = STATE_FILE):
        self.file_path = file_path
        self.profiles: Dict[str, UserProfile] = {}
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for uid, p_data in data.items():
                        # Filter out keys that are not in UserProfile to avoid errors
                        valid_keys = {
                            "user_id", "user_name", "likes", "dislikes", "order_history",
                            "predicted_interests", "cart", "current_step",
                            "temp_pay_method", "active_order_id", "last_activity_ts",
                            "browsing_product_id", "notify_when_available", "wishlist"
                        }
                        filtered_data = {k: v for k, v in p_data.items() if k in valid_keys}
                        self.profiles[str(uid)] = UserProfile(**filtered_data)
                logger.info(f"Loaded {len(self.profiles)} user profiles from {self.file_path}")
            except Exception as e:
                logger.error(f"Error loading state from {self.file_path}: {e}")

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                data = {uid: asdict(profile) for uid, profile in self.profiles.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving state to {self.file_path}: {e}")

    def get_profile(self, user_id: str) -> UserProfile:
        uid = str(user_id)
        if uid not in self.profiles:
            self.profiles[uid] = UserProfile(user_id=uid)
            self.save()
        return self.profiles[uid]

    def update_preferences(self, user_id: str, likes: List[str] = None, dislikes: List[str] = None):
        profile = self.get_profile(user_id)
        updated = False
        
        if likes:
            profile.likes = list(set(profile.likes + likes))
            updated = True
        if dislikes:
            profile.dislikes = list(set(profile.dislikes + dislikes))
            updated = True
            
        if updated:
            self.save()

    def add_order(self, user_id: str, order_data: Dict[str, Any]):
        profile = self.get_profile(user_id)
        profile.order_history.append(order_data)
        self.save()

# Global instance
user_store = UserAnalyticsStore()
