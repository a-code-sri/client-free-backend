from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Optional, Any, Dict,Literal
from datetime import datetime
from enum import Enum

class RoleEnum(str, Enum):
    freelancer = "Freelancer"
    client = "Client"
    both = "Both"

class ProjectStatus(str, Enum):
    open = "Open"
    in_progress = "In Progress"
    completed = "Completed"
    cancelled = "Cancelled"

class ProposalStatus(str, Enum):
    pending = "Pending"
    accepted = "Accepted"
    rejected = "Rejected"

class ProjectType(str, Enum):
    fixed = "Fixed"
    hourly = "Hourly"

class UserBase(BaseModel):
    email: str
    full_name: str
    role: RoleEnum
    profile_completeness: int = Field(default=0, ge=0, le=100)
    is_verified: bool = False
    is_pro: bool = False
    student_id: Optional[str] = None     
    linkedin_url: Optional[str] = None

class UserInDB(UserBase):
    user_id: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSignup(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=6, description="Stored in DB, never returned.")
    role: RoleEnum
    student_id: Optional[str] = None       
    linkedin_url: Optional[HttpUrl] = None 

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Education(BaseModel):
    institution: str
    degree: str
    start_year: int
    end_year: Optional[int] = None

class WorkExperience(BaseModel):
    company: str
    role: str
    start_date: str 
    end_date: Optional[str] = None
    description: str

class PortfolioProject(BaseModel):
    title: str
    description: str
    tech_stack: List[str]
    link: Optional[HttpUrl] = None
    images: List[HttpUrl] = []

class FreelancerPortfolio(BaseModel):
    user_id: str
    bio: str
    skills: List[str]
    hourly_rate: float
    availability_status: str
    education: List[Education] = []
    work_experience: List[WorkExperience] = []
    projects: List[PortfolioProject] = []
class TopCandidatePayload(BaseModel):
    challenge_id: str
    creator_id: str
    freelancer_id: str
class BudgetRange(BaseModel):
    min: float
    max: float

class ClientRequest(BaseModel):
    project_id: str
    client_id: str
    title: str
    description: str
    required_skills: List[str]
    budget_range: BudgetRange
    deadline: datetime
    project_type: ProjectType
    status: ProjectStatus = ProjectStatus.open
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Milestone(BaseModel):
    milestone_id: str
    title: str
    amount: float
    due_date: datetime
    is_approved: bool = False

class Proposal(BaseModel):
    proposal_id: str
    project_id: str
    freelancer_id: str
    bid_amount: float
    estimated_days: int
    cover_letter: str
    proposed_milestones: List[Milestone] = []
    attachments: List[HttpUrl] = []
    status: ProposalStatus = ProposalStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Contract(BaseModel):
    contract_id: str
    proposal_id: str
    project_id: str
    client_id: str
    freelancer_id: str
    total_amount: float
    active_milestones: List[Milestone]
    status: ProjectStatus = ProjectStatus.in_progress
    started_at: datetime = Field(default_factory=datetime.utcnow)

class Review(BaseModel):
    review_id: str
    contract_id: str
    reviewer_id: str
    reviewee_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClientReview(BaseModel):
    freelancer_id: str 
    client_id: str
    stars: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FullUserProfile(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr
    role: RoleEnum
    student_id: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    portfolio: Optional[Any] = None
    reviews: List[Any] = []
    rating: float = 0.0

class TransactionType(str, Enum):
    earning = "Earning"
    withdrawal = "Withdrawal"
    subscription = "Subscription"

class TransactionStatus(str, Enum):
    pending = "Pending"
    completed = "Completed"

class Transaction(BaseModel):
    transaction_id: str
    freelancer_id: str
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    type: TransactionType
    amount: float
    status: TransactionStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PendingPaymentRow(BaseModel):
    project_id: str
    client_id: str
    pending_amount: float

class WithdrawalRow(BaseModel):
    date: str
    amount: float

class EarningsDashboardResponse(BaseModel):
    total_earned: float
    total_commission_paid: float 
    pending_payments: List[PendingPaymentRow] 
    withdrawals: List[WithdrawalRow]     

class TestGenerationRequest(BaseModel):
    user_id: str
    skill: str

class TestSubmissionRequest(BaseModel):
    test_id: str
    user_id: str
    user_answers: Dict[str, str]    

class BookMark(BaseModel):
    client_id: str
    freelancers: List[str]

class verifiedSkills(BaseModel):
    client_id: str
    skill: str

# --- COMMUNITY SCHEMAS ---

class FeedPostCreate(BaseModel):
    author_id: str
    content: str = Field(..., max_length=1000)
    tags: List[str] = []

class ChallengeSubmission(BaseModel):
    challenge_id: str
    freelancer_id: str
    submission_url: HttpUrl
    description: str

class MentorshipOffer(BaseModel):
    mentor_id: str
    title: str
    description: str
    price: float = 0.0 
    duration_minutes: int = 60
    available_slots: int = 5

class ChallengeCreate(BaseModel):
    title: str
    description: str
    reward_badge: Literal["Creative Thinker","Problem Solver","Design Champion","Code Ninja"]
    deadline_days: int = 7


class ChallengeSubmissionPayload(BaseModel):
    challenge_id: str
    freelancer_id: str
    submission_url: HttpUrl
    description: str

class AcceptSubmissionPayload(BaseModel):
    challenge_id: str
    freelancer_id: str
    client_id: str

# --- NEW RESPONSE SCHEMAS FOR SWAGGER UI ---

class GenericMessageResponse(BaseModel):
    message: str
    is_liked: Optional[bool] = None

class FeedPostResponse(BaseModel):
    post_id: str
    author_id: str
    content: str
    tags: List[str]
    liked_by: List[str] = []
    comments: List[Any] = []
    created_at: datetime

class MentorshipSessionResponse(BaseModel):
    session_id: str
    mentor_id: str
    title: str
    description: str
    price: float
    duration_minutes: int
    available_slots: int
    booked_by: List[str] = []
    is_active: bool
    created_at: datetime

class UserMentorshipDashboard(BaseModel):
    user_id: str
    offered_sessions: List[MentorshipSessionResponse]
    booked_sessions: List[MentorshipSessionResponse]

class ChallengeSubmissionResponse(BaseModel):
    freelancer_id: str
    submission_url: str
    description: str
    upvotes: int
    submitted_at: datetime

class ChallengeResponse(BaseModel):
    challenge_id: str
    title: str
    description: str
    reward_badge: str
    deadline: datetime
    is_active: bool
    submissions: List[ChallengeSubmissionResponse] = []
    created_at: datetime