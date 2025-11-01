import asyncio
import cloudinary
import cloudinary.uploader
from typing import Any, Dict
from io import BytesIO
from decouple import config


CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = config("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET")
APPLICATION_FOLDER = config("APPLICATION_FOLDER", cast=str)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


class CloudinaryProvider:
    name = "cloudinary"

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_types: str,
        folder: str = APPLICATION_FOLDER,  # type: ignore
    ) -> Dict[str, Any]:
        """Uploads a file to Cloudinary."""

        def _sync_upload():
            upload_args = {
                "resource_type": "auto",
                "invalidate": True,
                "file_name": filename,
                "use_filename": True,
                "unique_filename": True,
                "content_type": content_types,
            }

            if folder:
                upload_args["folder"] = folder
            return cloudinary.uploader.upload(BytesIO(file_bytes), **upload_args)

        result = await asyncio.to_thread(_sync_upload)
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "resource_type": result.get("resource_type"),
            "raw": result,
        }

    async def delete_file(self, public_id: str, resource_type: str = "image") -> bool:
        """Deletes a file from Cloudinary"""

        def _sync_destroy():
            return cloudinary.uploader.destroy(
                public_id=public_id, resource_type=resource_type
            )

        result = await asyncio.to_thread(_sync_destroy)
        return result.get("result") in ("ok", "not found")
