import asyncio
from types import SimpleNamespace
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.product_media import ProductMedia
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import product_media as pm_service


class DummyRes:
    def __init__(self, vals):
        self._vals = vals

    def scalars(self):
        class S:
            def __init__(self, v):
                self._v = v

            def all(self):
                return self._v

            def one_or_none(self):
                return self._v

        return S(self._vals)

    def scalar_one_or_none(self):
        return self._vals


class DB:
    def __init__(self, execute_result=None):
        self._execute_result = execute_result
        self.added = []
        self.deleted = []

    async def execute(self, q):
        await asyncio.sleep(0)
        return self._execute_result

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        await asyncio.sleep(0)

    async def refresh(self, obj):
        await asyncio.sleep(0)

    async def delete(self, obj):
        await asyncio.sleep(0)
        self.deleted.append(obj)


@pytest.mark.asyncio
async def test_validate_media_and_add_missing_raises():
    prod = SimpleNamespace(id=uuid4())
    with pytest.raises(HTTPException):
        await pm_service._validate_media_and_add(
            db=cast(AsyncSession, DB(execute_result=DummyRes([]))),
            product=cast(Product, prod),
            media_ids=[uuid4()],
        )


@pytest.mark.asyncio
async def test_get_and_list_and_create_and_delete_flow(monkeypatch):
    # get_product_media
    pm = SimpleNamespace(id=uuid4(), product_id=uuid4())
    res = await pm_service.get_product_media(
        session=cast(AsyncSession, DB(execute_result=DummyRes(pm))), pm_id=pm.id
    )
    assert res == pm

    # list_product_media
    items = [pm]
    res2 = await pm_service.list_product_media(
        session=cast(AsyncSession, DB(execute_result=DummyRes(items))),
        product_id=pm.product_id,
    )
    assert res2 == items

    # create_product_media: product exists and media exists (tested separately below)
    # delete only (delete should simply call session.delete)
    pm_obj = SimpleNamespace(id=pm.id)
    db_del = DB()
    await pm_service.delete_product_media(
        session=cast(AsyncSession, db_del), pm=cast(ProductMedia, pm_obj)
    )
    assert pm_obj in db_del.deleted


@pytest.mark.asyncio
async def test_create_product_media_and_update_variant_only(monkeypatch):
    product = SimpleNamespace(id=uuid4())
    media = SimpleNamespace(id=uuid4())

    # Exec sequence for select(Product) then select(Media)
    class ExecSeq:
        def __init__(self, seq):
            self.seq = seq

        def scalars(self):
            class S:
                def __init__(self, v):
                    self.v = v

                def one_or_none(self):
                    return self.v

            return S(self.seq.pop(0))

        def scalar_one_or_none(self):
            return self.seq.pop(0)

    db_create = DB(execute_result=ExecSeq([product, media]))

    # monkeypatch ProductMedia to avoid SQLAlchemy ORM init when instantiating
    monkeypatch.setattr(
        pm_service, "ProductMedia", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    created = await pm_service.create_product_media(
        session=cast(AsyncSession, db_create), product_id=product.id, media_id=media.id
    )
    assert getattr(created, "product_id", None) == product.id

    # update only variant (do not flip is_primary to avoid SQL update calls)
    pm_obj = SimpleNamespace(
        product_id=product.id, media_id=media.id, variant_id=None, is_primary=False
    )
    db_upd = DB()
    updated = await pm_service.update_product_media(
        session=cast(AsyncSession, db_upd),
        pm=cast(ProductMedia, pm_obj),
        variant_id=uuid4(),
        is_primary=None,
    )
    assert updated.variant_id is not None
