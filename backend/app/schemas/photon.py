"""Photon Schemas - Photon system request/response models"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.shop import PhotonTransactionType

# ========== Photon Balance Schemas ==========

class PhotonBalance(BaseModel):
    """User photon balance information"""
    user_id: UUID = Field(description="User ID")
    balance: int = Field(description="Current photon balance")
    updated_at: datetime | None = Field(default=None, description="Last update time")

    class Config:
        from_attributes = True


class PhotonBalanceResponse(BaseModel):
    """Photon balance response"""
    success: bool = Field(default=True)
    data: PhotonBalance = Field(description="Photon balance info")


# ========== Photon Transaction Schemas ==========

class PhotonTransactionItem(BaseModel):
    """Photon transaction item"""
    id: UUID = Field(description="Transaction ID")
    transaction_type: PhotonTransactionType = Field(description="Transaction type")
    amount: int = Field(description="Amount (positive for income, negative for expense)")
    balance_before: int = Field(description="Balance before transaction")
    balance_after: int = Field(description="Balance after transaction")
    source: str | None = Field(default=None, description="Source description")
    related_item_id: str | None = Field(default=None, description="Related item ID")
    extra_data: dict[str, Any] | None = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(description="Transaction time")

    @property
    def is_income(self) -> bool:
        """Is income transaction"""
        return self.amount > 0

    @property
    def is_expense(self) -> bool:
        """Is expense transaction"""
        return self.amount < 0

    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """Transaction history response"""
    success: bool = Field(default=True)
    data: list[PhotonTransactionItem] = Field(default_factory=list, description="Transaction history")
    meta: dict[str, Any] = Field(default_factory=dict, description="Pagination info")


class TransactionSummary(BaseModel):
    """Transaction summary statistics"""
    total_income: int = Field(default=0, description="Total income")
    total_expense: int = Field(default=0, description="Total expense")
    net_change: int = Field(default=0, description="Net change")
    transaction_count: int = Field(default=0, description="Total transactions")
    by_type: dict[str, int] = Field(default_factory=dict, description="Breakdown by type")


class TransactionSummaryResponse(BaseModel):
    """Transaction summary response"""
    success: bool = Field(default=True)
    data: TransactionSummary = Field(description="Transaction summary")
    meta: dict[str, Any] = Field(default_factory=dict, description="Time period info")


# ========== Photon Transfer Schemas ==========

class PhotonTransferRequest(BaseModel):
    """Photon transfer request"""
    recipient_id: UUID = Field(description="Recipient user ID")
    amount: int = Field(gt=0, description="Amount to transfer")
    message: str | None = Field(default=None, max_length=200, description="Optional message")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 10000:  # Daily transfer limit
            raise ValueError('Amount cannot exceed 10000 photons per transfer')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "recipient_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 100,
                "message": "Good job on your achievement!"
            }
        }


class PhotonTransferResponse(BaseModel):
    """Photon transfer response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: dict[str, Any] = Field(description="Transfer details")
    transfer_id: UUID = Field(description="Transfer transaction ID")
    sender_balance_before: int = Field(description="Sender balance before")
    sender_balance_after: int = Field(description="Sender balance after")
    recipient_username: str | None = Field(default=None, description="Recipient username")
    amount_transferred: int = Field(description="Amount transferred")


# ========== Photon Grant/Deduct Schemas (Admin) ==========

class PhotonAdjustmentRequest(BaseModel):
    """Photon adjustment request (admin only)"""
    user_id: UUID = Field(description="User ID to adjust")
    amount: int = Field(description="Amount to adjust (positive to grant, negative to deduct)")
    reason: str = Field(description="Reason for adjustment")
    transaction_type: PhotonTransactionType = Field(description="Transaction type")
    related_item_id: str | None = Field(default=None, description="Related item ID")
    extra_data: dict[str, Any] | None = Field(default=None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 500,
                "reason": "Achievement reward: First sprint completion",
                "transaction_type": "grant_achievement",
                "related_item_id": "sprint_first_complete"
            }
        }


class PhotonAdjustmentResponse(BaseModel):
    """Photon adjustment response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: PhotonBalance = Field(description="Updated balance info")
