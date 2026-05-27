from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import certifi 

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_URI")

if not MONGO_DETAILS:
    raise ValueError("FATAL ERROR: MONGO_URI is not set in the .env file.")

client = AsyncIOMotorClient(
    MONGO_DETAILS, 
    tls=True, 
    tlsAllowInvalidCertificates=True
)

# Define the database
database = client.talentstage_db

# Expose collections
user_collection = database.get_collection("users")
freelancer_portfolio_collection = database.get_collection("freelancer_portfolios")
client_request_collection = database.get_collection("client_requests")
proposal_collection = database.get_collection("proposals")
contract_collection = database.get_collection("contracts")
review_collection = database.get_collection("reviews")
transaction_collection = database.get_collection("transactions")
skill_test_collection = database.get_collection("skill_tests")
taxonomy_collection = database.get_collection("skills_taxonomy")
verified_skills=database.get_collection("verified_skills")
client_bookMarks_collection=database.get_collection("client_bookMarks")
feed_collection = database.get_collection("community_feed")
challenge_collection = database.get_collection("skill_challenges")
mentorship_collection = database.get_collection("mentorship_sessions")