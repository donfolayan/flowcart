# @router.get(
#     "/{product_id}",
#     description="Get all media for a product",
#     response_model=List[MediaResponse],
#     status_code=status.HTTP_200_OK,
# )
# async def get_all_product_media(
#     product_id: UUID, db: AsyncSession = Depends(get_session)
# ) -> List[MediaResponse]:
#     # Check if the product exists
#     product_query = select(Product).where(Product.id == product_id):
#     product_result = await db.execute(product_query)
#     product: Optional[Product] = product_result.scalars().one_or_none()

#     if not product:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
#         )

#     # Fetch all media associated with the product
#     q = select(Media).where(Media.product_id == product_id)
#     r = await db.execute(q)
#     media_items: List[Media] = list(r.scalars().all())

#     return [MediaResponse.model_validate(media) for media in media_items]
