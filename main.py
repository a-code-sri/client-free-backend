from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from routes import contract_routes, review_routes, portfolio_routes, ai_routes, marketplace_routes, user_routes, earnings_routes, book_marks_routes, valid_skils_routes, community_routes
from ai.taxonomy import load_taxonomy
from services.badge_service import run_system_badge_assignment

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Taxonomy...")
    await load_taxonomy()
    
    print("Starting Background Scheduler...")
    scheduler.add_job(run_system_badge_assignment, 'cron', hour=2, minute=0)
    scheduler.start()
    
    yield  
    print("Stopping Background Scheduler...")
    scheduler.shutdown()

app = FastAPI(
    title="TalentStage API",
    version="1.0.0",
    lifespan=lifespan 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router, prefix="/api/users", tags=["Users"])
app.include_router(marketplace_routes.router, prefix="/api/marketplace", tags=["Marketplace"]) 
app.include_router(ai_routes.router, prefix="/api/ai", tags=["AI Copilot"]) 
app.include_router(portfolio_routes.router, prefix="/api/portfolios", tags=["Portfolios"]) 
app.include_router(review_routes.router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(earnings_routes.router, prefix="/api/earnings", tags=["Earnings"])
app.include_router(contract_routes.router, prefix="/api/contracts", tags=["Contracts"])
app.include_router(book_marks_routes.router, prefix="/api/bookmarks",tags=["BookMarks"])
app.include_router(valid_skils_routes.router, prefix="/api/verified_skills",tags=["Verified_skills"])
app.include_router(
    community_routes.router, 
    prefix="/api/community", 
    tags=["Community & Mentorship"]
)
@app.get("/")
async def root():
    return {"message": "Welcome to the TalentStage API. Go to /docs for Swagger."}