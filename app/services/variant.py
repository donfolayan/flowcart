from uuid import UUID
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logs.logging_utils import get_logger
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.product_variant import ProductVariantCreate, ProductVariantUpdate

logger = get_logger("app.variant")


class VariantService:
    """Business logic for product variants."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, variant_id: UUID) -> ProductVariant:
        q = select(ProductVariant).where(ProductVariant.id == variant_id)
        r = await self.db.execute(q)
        variant: Optional[ProductVariant] = r.scalars().one_or_none()

        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product variant not found",
            )
        return variant

    async def list_by_product(self, product_id: UUID) -> List[ProductVariant]:
        q = select(ProductVariant).where(ProductVariant.product_id == product_id)
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def create(
        self, product_id: UUID, payload: ProductVariantCreate
    ) -> ProductVariant:
        payload_data = payload.model_dump()

        if not payload_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload - no data provided",
            )

        product_query = select(Product).where(Product.id == product_id)
        result_query = await self.db.execute(product_query)
        base_product = result_query.scalars().one_or_none()

        if base_product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base product not found",
            )

        variant = ProductVariant(**payload_data, product_id=product_id)
        variant.product_id = product_id

        try:
            self.db.add(variant)
            await self.db.commit()
            await self.db.refresh(variant)
        except Exception as e:
            logger.exception(
                "Failed to create product variant",
                extra={"product_id": str(product_id), "payload": payload.model_dump()},
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create product variant",
            ) from e

        return variant

    async def delete(self, variant_id: UUID) -> None:
        q = select(ProductVariant).where(ProductVariant.id == variant_id)
        r = await self.db.execute(q)
        variant: Optional[ProductVariant] = r.scalars().one_or_none()

        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product variant not found",
            )

        try:
            await self.db.execute(
                delete(ProductVariant).where(ProductVariant.id == variant_id)
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to delete product variant",
                extra={"variant_id": str(variant_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete product variant",
            ) from e

    async def delete_by_product(self, product_id: UUID) -> None:
        q = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .limit(1)
        )
        r = await self.db.execute(q)
        exists: Optional[ProductVariant] = r.scalars().one_or_none()

        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No variants found for the product",
            )

        try:
            query = delete(ProductVariant).where(
                ProductVariant.product_id == product_id
            )
            await self.db.execute(query)
            await self.db.commit()
        except IntegrityError as e:
            logger.debug(
                "IntegrityError on deleting product variants",
                extra={"product_id": str(product_id)},
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete product variants due to existing dependencies",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to delete product variants",
                extra={"product_id": str(product_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete product variants",
            ) from e

    async def update(
        self, variant_id: UUID, payload: ProductVariantUpdate
    ) -> ProductVariant:
        q = select(ProductVariant).where(ProductVariant.id == variant_id)
        r = await self.db.execute(q)
        variant: Optional[ProductVariant] = r.scalars().one_or_none()

        if not variant:
            logger.info(
                "Product variant not found for update",
                extra={"variant_id": str(variant_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product variant not found",
            )

        update_data = payload.model_dump(exclude_unset=True)

        if "sku" in update_data and update_data["sku"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU cannot be null",
            )
        if "name" in update_data and update_data["name"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name cannot be null",
            )

        if "sku" in update_data and update_data["sku"] != getattr(variant, "sku", None):
            existing_q = select(ProductVariant).where(
                ProductVariant.sku == update_data["sku"],
                ProductVariant.id != variant_id,
            )
            existing_r = await self.db.execute(existing_q)
            existing_variant = existing_r.scalars().one_or_none()
            if existing_variant:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="SKU already exists",
                )

        for key, value in update_data.items():
            setattr(variant, key, value)

        try:
            self.db.add(variant)
            await self.db.commit()
            await self.db.refresh(variant)
        except (IntegrityError, DataError) as e:
            await self.db.rollback()
            logger.debug(
                "Constraint violation updating product variant",
                extra={
                    "variant_id": str(variant_id),
                    "payload": payload.model_dump(exclude_unset=True),
                    "error": str(e),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Update violates database constraints (e.g., unique SKU, non-negative checks, or enum status)"
                ),
            ) from e
        except Exception as e:
            logger.exception(
                "Failed to update product variant",
                extra={
                    "variant_id": str(variant_id),
                    "payload": payload.model_dump(exclude_unset=True),
                },
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update product variant",
            ) from e

        return variant
