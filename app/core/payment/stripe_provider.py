import stripe
import asyncio
from stripe import StripeError
from .base import PaymentProvider
from app.core.config import config
from .payment_error import PaymentError
from typing import Optional, Dict, Any, Callable


STRIPE_API_KEY = config.STRIPE_API_KEY
STRIPE_WEBHOOK_SECRET = config.STRIPE_WEBHOOK_SECRET

if STRIPE_API_KEY:
    try:
        stripe.api_key = STRIPE_API_KEY
    except Exception:
        stripe.api_key = None


class StripeProvider(PaymentProvider):
    """
    Minimal Stripe provider for PaymentIntent flows (create/authorize/capture/refund/cancel)
    - `amount_cents` must be integer in smallest currency unit (e.g., cents).
    - `payment_method_data` should follow Stripe's payment_method_data shape if using
    raw card or token-based confirmation.
    """

    name = "stripe"

    def __init__(self, client: Optional[Any] = None):
        self.client = client or stripe
        # set api key if available
        if STRIPE_API_KEY:
            try:
                # stripe module exposes api_key attribute
                setattr(self.client, "api_key", STRIPE_API_KEY)
            except Exception as e:
                raise PaymentError(f"Failed to configure stripe client: {e}") from e

    async def _run_in_thread(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """Run a synchronous function in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(lambda: fn(*args, **kwargs))

    # small helper to standardize Stripe responses
    @staticmethod
    def _sanitize_intent(intent: Any) -> Dict[str, Any]:
        raw = None
        if hasattr(intent, "to_dict"):
            try:
                raw = intent.to_dict()
            except Exception:
                raw = None
        elif isinstance(intent, dict):
            raw = intent

        if raw is None:
            return {"id": None, "status": None, "client_secret": None, "raw": None}

        return {
            "id": raw.get("id"),
            "status": raw.get("status"),
            "client_secret": raw.get("client_secret"),
            "raw": raw,
        }

    async def charge(
        self,
        amount_cents: int,
        currency: str,
        payment_method_data: Dict[str, Any],
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        capture: bool = True,
    ) -> Dict[str, Any]:
        """
        Create (and optionally confirm/capture) a PaymentIntent.
        """

        def _sync_create():
            kwargs = {
                "amount": amount_cents,
                "currency": currency,
                "payment_method_data": payment_method_data,
                "confirm": True,
                "capture_method": "automatic" if capture else "manual",
            }
            if description:
                kwargs["description"] = description
            # idempotency_key is passed via request_options to stripe-python
            request_options = (
                {"idempotency_key": idempotency_key} if idempotency_key else None
            )

            if request_options:
                _kwargs = dict(kwargs)
                _kwargs["request_options"] = request_options
                return self.client.PaymentIntent.create(**_kwargs)
            return self.client.PaymentIntent.create(**kwargs)

        try:
            intent = await self._run_in_thread(_sync_create)
            return self._sanitize_intent(intent)
        except StripeError as e:
            # preserve Stripe error information
            raise PaymentError(
                f"Stripe error creating PaymentIntent: {e.user_message or str(e)}"
            ) from e
        except Exception as e:
            raise PaymentError(f"Unexpected error creating PaymentIntent: {e}") from e

    async def authorize(
        self,
        amount_cents: int,
        currency: str,
        payment_method_data: Dict[str, Any],
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.charge(
            amount_cents=amount_cents,
            currency=currency,
            payment_method_data=payment_method_data,
            description=description,
            idempotency_key=idempotency_key,
            capture=False,
        )

    async def capture(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        def _sync_capture():
            if amount_cents is not None:
                return self.client.PaymentIntent.capture(
                    payment_intent_id, amount_to_capture=amount_cents
                )
            return self.client.PaymentIntent.capture(payment_intent_id)

        try:
            intent = await self._run_in_thread(_sync_capture)
            return self._sanitize_intent(intent)
        except StripeError as e:
            raise PaymentError(
                f"Stripe error capturing PaymentIntent: {e.user_message or str(e)}"
            ) from e
        except Exception as e:
            raise PaymentError(f"Unexpected error capturing PaymentIntent: {e}") from e

    async def refund(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        def _sync_refund():
            kwargs: Dict[str, Any] = {"payment_intent": payment_intent_id}
            if amount_cents is not None:
                kwargs["amount"] = amount_cents
            return self.client.Refund.create(**kwargs)

        try:
            refund = await self._run_in_thread(_sync_refund)
            return {
                "id": getattr(refund, "id", None) or refund.get("id"),
                "status": getattr(refund, "status", None) or refund.get("status"),
                "raw": dict(refund)
                if hasattr(refund, "to_dict") or isinstance(refund, dict)
                else None,
            }
        except StripeError as e:
            raise PaymentError(
                f"Stripe error creating refund: {e.user_message or str(e)}"
            ) from e
        except Exception as e:
            raise PaymentError(f"Unexpected error creating refund: {e}") from e

    async def void(self, payment_intent_id: str) -> Dict[str, Any]:
        def _sync_cancel():
            return self.client.PaymentIntent.cancel(payment_intent_id)

        try:
            res = await self._run_in_thread(_sync_cancel)
            return {
                "id": getattr(res, "id", None) or res.get("id"),
                "status": getattr(res, "status", None) or res.get("status"),
                "raw": dict(res)
                if hasattr(res, "to_dict") or isinstance(res, dict)
                else None,
            }
        except StripeError as e:
            raise PaymentError(
                f"Stripe error cancelling PaymentIntent: {e.user_message or str(e)}"
            ) from e
        except Exception as e:
            raise PaymentError(f"Unexpected error cancelling PaymentIntent: {e}") from e

    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Validate and parse a stripe webhook payload. Returns a sanitized dict:
        { "type": <event.type>, "data": <event.data.object (dict)> }
        """

        def _sync_construct_event():
            if not STRIPE_WEBHOOK_SECRET:
                raise PaymentError("Stripe webhook secret not configured")
            return self.client.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )

        try:
            event = await self._run_in_thread(_sync_construct_event)
            # event is a Stripe Event object; sanitize:
            etype = getattr(event, "type", None) or event.get("type")
            data_obj = getattr(event, "data", None)
            data_obj = (
                data_obj.get("object")
                if isinstance(data_obj, dict) and "object" in data_obj
                else getattr(data_obj, "object", None)
            )
            # convert stripe objects to dict where possible
            data_dict = (
                data_obj.to_dict()
                if (data_obj is not None and hasattr(data_obj, "to_dict"))
                else (dict(data_obj) if isinstance(data_obj, dict) else None)
            )
            raw_event = (
                event.to_dict()
                if (event is not None and hasattr(event, "to_dict"))
                else (dict(event) if isinstance(event, dict) else None)
            )
            return {"type": etype, "data": data_dict, "raw": raw_event}
        except StripeError as e:
            raise PaymentError(
                f"Stripe webhook verification failed: {e.user_message or str(e)}"
            ) from e
        except Exception as e:
            raise PaymentError(f"Unexpected error verifying webhook: {e}") from e

    async def health_check(self) -> bool:
        try:

            def _sync_ping():
                return self.client.Balance.retrieve()

            await self._run_in_thread(_sync_ping)
            return True
        except Exception:
            return False
