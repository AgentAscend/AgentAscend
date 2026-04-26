from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DashboardStat(BaseModel):
    label: str
    value: str
    change: str
    change_type: Literal["positive", "negative", "neutral"] = "neutral"


class DashboardAgent(BaseModel):
    agent_id: str
    name: str
    category: str
    status: Literal["active", "idle", "paused", "error"]
    task: str
    success_rate: float


class DashboardActivity(BaseModel):
    source: str
    action: str
    occurred_at: str


class DashboardOverviewResponse(BaseModel):
    status: Literal["ok"] = "ok"
    stats: list[DashboardStat]
    active_agents: list[DashboardAgent]
    recent_activity: list[DashboardActivity]


class AgentRecord(BaseModel):
    agent_id: str
    name: str
    category: str
    description: str
    status: Literal["active", "idle", "paused", "error"]
    tasks_completed: int = 0
    success_rate: float = 0.0
    created_at: str
    updated_at: str


class AgentListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    agents: list[AgentRecord]


class AgentActionRequest(BaseModel):
    action: Literal["start", "pause", "resume"]


class AgentActionResponse(BaseModel):
    status: Literal["ok"] = "ok"
    agent: AgentRecord


class DeploymentRecord(BaseModel):
    deployment_id: str
    name: str
    environment: str
    status: Literal["running", "paused", "error"]
    region: str
    agents_count: int
    cpu_percent: int = 0
    memory_percent: int = 0
    requests_per_day: int = 0
    created_at: str
    updated_at: str


class DeploymentListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    deployments: list[DeploymentRecord]


class DeploymentActionRequest(BaseModel):
    action: Literal["pause", "resume", "restart"]


class DeploymentActionResponse(BaseModel):
    status: Literal["ok"] = "ok"
    deployment: DeploymentRecord


class WorkflowRecord(BaseModel):
    workflow_id: str
    name: str
    status: Literal["active", "paused", "draft"]
    runs_total: int = 0
    success_rate: float = 0.0
    updated_at: str


class WorkflowRunRecord(BaseModel):
    run_id: str
    workflow_id: str
    status: Literal["success", "failed", "running"]
    duration_ms: int = 0
    started_at: str


class WorkflowListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    workflows: list[WorkflowRecord]
    recent_runs: list[WorkflowRunRecord]


class ExecutionRecord(BaseModel):
    execution_id: str
    source_type: str | None = None
    source_id: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionEventRecord(BaseModel):
    event_id: str
    execution_id: str
    step_id: str | None = None
    event_type: str
    level: str
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ExecutionArtifactRecord(BaseModel):
    artifact_id: str
    execution_id: str
    step_id: str | None = None
    artifact_type: str
    name: str
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ExecutionStepRecord(BaseModel):
    step_id: str
    execution_id: str
    step_order: int
    step_type: str
    name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionCostRecord(BaseModel):
    cost_id: str
    execution_id: str
    step_id: str | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_amount: float = 0
    cost_currency: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ExecutionApprovalRecord(BaseModel):
    approval_id: str
    execution_id: str
    step_id: str | None = None
    approval_type: str
    status: str
    requested_by: str | None = None
    approved_by: str | None = None
    requested_at: str
    decided_at: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    executions: list[ExecutionRecord]


class ExecutionDetailResponse(BaseModel):
    status: Literal["ok"] = "ok"
    execution: ExecutionRecord
    steps: list[ExecutionStepRecord] = Field(default_factory=list)
    events: list[ExecutionEventRecord] = Field(default_factory=list)
    artifacts: list[ExecutionArtifactRecord] = Field(default_factory=list)
    costs: list[ExecutionCostRecord] = Field(default_factory=list)
    approvals: list[ExecutionApprovalRecord] = Field(default_factory=list)


class TaskRecord(BaseModel):
    task_id: str
    user_id: str | None = None
    agent_id: str | None = None
    type: str = "general"
    title: str
    status: Literal["queued", "running", "completed", "failed"]
    priority: Literal["low", "medium", "high"]
    assigned_to: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    tasks: list[TaskRecord]


class OutputRecord(BaseModel):
    output_id: str
    task_id: str | None = None
    user_id: str | None = None
    title: str
    output_type: str
    content: str | None = None
    text: str | None = None
    file_url: str | None = None
    size_bytes: int
    download_url: str
    created_at: str


class OutputListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    outputs: list[OutputRecord]


class CommunityPost(BaseModel):
    post_id: str
    author_user_id: str
    title: str
    body: str
    likes: int = 0
    created_at: str
    updated_at: str


class LeaderboardEntry(BaseModel):
    user_id: str
    score: int


class CommunityResponse(BaseModel):
    status: Literal["ok"] = "ok"
    posts: list[CommunityPost]
    leaderboard: list[LeaderboardEntry]


class UserPreferences(BaseModel):
    notifications_email: bool = True
    notifications_push: bool = True
    notifications_marketing: bool = False
    theme: Literal["dark", "light", "system"] = "dark"


class UserPreferencesResponse(BaseModel):
    status: Literal["ok"] = "ok"
    preferences: UserPreferences


class UserPreferencesPatchRequest(BaseModel):
    notifications_email: bool | None = None
    notifications_push: bool | None = None
    notifications_marketing: bool | None = None
    theme: Literal["dark", "light", "system"] | None = None


class AvatarUpdateRequest(BaseModel):
    avatar_url: str = Field(min_length=1)


class AvatarUpdateResponse(BaseModel):
    status: Literal["ok"] = "ok"
    avatar_url: str


class SearchResult(BaseModel):
    result_type: str
    result_id: str
    title: str
    subtitle: str


class SearchResponse(BaseModel):
    status: Literal["ok"] = "ok"
    query: str
    results: list[SearchResult]


class NotificationRecord(BaseModel):
    notification_id: str
    user_id: str
    title: str
    message: str
    is_read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    notifications: list[NotificationRecord]


class NotificationMarkReadResponse(BaseModel):
    status: Literal["ok"] = "ok"
    notification_id: str
    is_read: bool


class TokenBalancesResponse(BaseModel):
    status: Literal["ok"] = "ok"
    user_id: str
    asnd_balance: str
    sol_balance: str
    staking_balance: str
    pending_rewards: str


class TokenHistoryRecord(BaseModel):
    tx_signature: str | None
    token: str
    amount: str
    status: str
    created_at: str


class TokenHistoryResponse(BaseModel):
    status: Literal["ok"] = "ok"
    user_id: str
    history: list[TokenHistoryRecord]


class MarketplaceBrowseRecord(BaseModel):
    listing_id: str
    creator_user_id: str
    title: str
    description: str
    category: str
    pricing_model: str
    price_amount: float
    price_token: str
    published_at: str | None = None


class MarketplaceBrowseResponse(BaseModel):
    status: Literal["ok"] = "ok"
    listings: list[MarketplaceBrowseRecord]


class EntitlementRecord(BaseModel):
    listing_id: str
    user_id: str
    installed_at: str


class EntitlementsResponse(BaseModel):
    status: Literal["ok"] = "ok"
    entitlements: list[EntitlementRecord]


class InstallListingRequest(BaseModel):
    user_id: str


class InstallListingResponse(BaseModel):
    status: Literal["ok"] = "ok"
    entitlement: EntitlementRecord


class CreatorPayoutTotalsResponse(BaseModel):
    status: Literal["ok"] = "ok"
    creator_user_id: str
    pending_amount: str
    paid_amount: str
