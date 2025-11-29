from typing import Any, Dict, BinaryIO, Optional, Protocol, Union


class StorageProvider(Protocol):
    """Protocol describing storage providers used by the app.

    Implementations should perform any blocking network I/O in a thread
    (for example with `asyncio.to_thread`) so their public methods remain
    async-friendly.
    """

    name: str

    async def upload_file(
        self,
        file: Union[bytes, BinaryIO],
        filename: Optional[str],
        content_type: Optional[str],
        folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload `file` and return a normalized dict with keys:
        - `url`: public URL (if available)
        - `public_id`: provider-specific id/key
        - `resource_type`: optional (e.g. 'image'/'video')
        - `raw`: raw provider response
        """
        ...

    async def delete_file(self, public_id: str, resource_type: str = "image") -> bool:
        """Delete the resource identified by `public_id`.

        Return True when the resource is known deleted or did not exist (idempotent).
        """
        ...
