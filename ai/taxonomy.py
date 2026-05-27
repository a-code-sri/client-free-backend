import asyncio
from utils.database import taxonomy_collection

HARDCODED_SKILL_TAXONOMY = {}

async def _fetch_all_taxonomy() -> dict:
    taxonomy_data = {}
    try:
        cursor = taxonomy_collection.find({})
        
        async for document in cursor:
            document.pop("_id", None)
            
            key = document.get("category")
            
            if key:
                taxonomy_data[key] = document.get("skills", document)
            else:
                taxonomy_data.update(document)
                
        return taxonomy_data
    except Exception as e:
        print(f"Error fetching taxonomy from DB: {e}")
        return None

async def load_taxonomy():
    global HARDCODED_SKILL_TAXONOMY
    fetched_data = await _fetch_all_taxonomy()
    
    if fetched_data is None:
        print("Warning: Failed to load taxonomy or database returned None.")
    else:
        HARDCODED_SKILL_TAXONOMY.clear()
        HARDCODED_SKILL_TAXONOMY.update(fetched_data)
        print("Successfully loaded taxonomy data into memory.")