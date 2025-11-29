from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PaymentProvider(ABC):
    """Base abstract class for payment providers."""

    @abstractmethod
    async def charge(
        self,
        amount_cents: int,
        currency: str,
        payment_method_data: Dict[str, Any],
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        capture: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a charge or payment intent."""
        raise NotImplementedError

    @abstractmethod
    async def authorize(
        self,
        amount_cents: int,
        currency: str,
        payment_method_data: Dict[str, Any],
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Authorize a payment without capturing funds."""
        raise NotImplementedError

    @abstractmethod
    async def capture(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Capture previously authorized funds."""
        raise NotImplementedError

    @abstractmethod
    async def refund(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Refund a payment, either full or partial."""
        raise NotImplementedError

    @abstractmethod
    async def void(
        self,
        payment_intent_id: str,
    ) -> Dict[str, Any]:
        """Void a previously authorized payment."""
        raise NotImplementedError
