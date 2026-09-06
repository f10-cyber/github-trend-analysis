import os
import json
import redis
from dotenv import load_dotenv
from extract_topics_spacy import get_top_topics_for_category

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)

CATEGORIES = ["web-dev", "ai", "data-science", "cyber-security", "mobile"]
TTL_SECONDS = 60 * 60 * 24  # 24 jam

def main():
    for category in CATEGORIES:
        print(f"Menghitung topik untuk kategori: {category} ...")
        results = get_top_topics_for_category(category)
        payload = {
            "category": category,
            "data": [{"topik": phrase, "frekuensi": count} for phrase, count in results],
        }
        redis_client.setex(f"topik:{category}", TTL_SECONDS, json.dumps(payload))
        print(f"  Selesai, {len(results)} topik disimpan ke Redis (berlaku 24 jam)")

if __name__ == "__main__":
    main()
