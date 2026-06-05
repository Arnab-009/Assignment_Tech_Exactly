"""Google Drive integration service.

Wraps the Google Drive v3 API to list and download files from a folder. All
blocking Google client calls are dispatched to a threadpool so they never block
the FastAPI event loop.
"""
from __future__ import annotations

import io
import logging

from fastapi.concurrency import run_in_threadpool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from app.exceptions import (
    DriveApiError,
    DrivePermissionError,
    FolderNotFoundError,
)
from app.models.schemas import DriveFile, DriveFolder

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
TXT_MIME = "text/plain"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

# MIME types we can extract text from. Google Docs are exported to text/plain.
SUPPORTED_MIME_TYPES = frozenset({PDF_MIME, DOCX_MIME, TXT_MIME, GOOGLE_DOC_MIME})

_LIST_FIELDS = "nextPageToken, files(id, name, mimeType, webViewLink, size)"


class DriveService:
    """Thin async wrapper over the Google Drive v3 API."""

    def __init__(self, max_files: int = 20, max_file_size_bytes: int = 10 * 1024 * 1024) -> None:
        self._max_files = max_files
        self._max_file_size_bytes = max_file_size_bytes

    # -- Public async API ---------------------------------------------------
    async def list_folders(self, credentials: Credentials) -> list[DriveFolder]:
        """List all Drive folders visible to the authenticated user."""
        return await run_in_threadpool(self._list_folders_sync, credentials)

    async def list_files(
        self, folder_id: str, credentials: Credentials
    ) -> list[DriveFile]:
        """List supported, non-trashed files inside ``folder_id``."""
        return await run_in_threadpool(self._list_files_sync, folder_id, credentials)

    async def download_for_parsing(
        self, file: DriveFile, credentials: Credentials
    ) -> tuple[bytes, str]:
        """Download a file's bytes and the MIME type to parse it as.

        Google Docs have no binary download, so they are exported to
        ``text/plain``; the returned MIME type reflects what to parse as.
        """
        return await run_in_threadpool(
            self._download_for_parsing_sync, file, credentials
        )

    # -- Sync implementations (run in threadpool) ---------------------------
    def _build(self, credentials: Credentials):
        return build(
            "drive", "v3", credentials=credentials, cache_discovery=False
        )

    def _list_folders_sync(self, credentials: Credentials) -> list[DriveFolder]:
        service = self._build(credentials)
        folders: list[DriveFolder] = []
        page_token: str | None = None
        query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        try:
            while True:
                response = (
                    service.files()
                    .list(
                        q=query,
                        fields="nextPageToken, files(id, name)",
                        pageSize=200,
                        pageToken=page_token,
                        orderBy="name",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for raw in response.get("files", []):
                    folders.append(DriveFolder(id=raw["id"], name=raw.get("name", "Untitled")))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as exc:
            raise self._translate_http_error(exc, "folders") from exc
        return folders

    def _list_files_sync(
        self, folder_id: str, credentials: Credentials
    ) -> list[DriveFile]:
        service = self._build(credentials)
        query = f"'{folder_id}' in parents and trashed = false"
        files: list[DriveFile] = []
        page_token: str | None = None

        try:
            while True:
                response = (
                    service.files()
                    .list(
                        q=query,
                        fields=_LIST_FIELDS,
                        pageSize=100,
                        pageToken=page_token,
                        orderBy="name",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for raw in response.get("files", []):
                    if raw.get("mimeType") not in SUPPORTED_MIME_TYPES:
                        continue
                    size = raw.get("size")
                    size_int = int(size) if size is not None else None
                    if size_int and size_int > self._max_file_size_bytes:
                        logger.info(
                            "Skipping oversized file '%s' (%d bytes)",
                            raw.get("name"),
                            size_int,
                        )
                        continue
                    files.append(
                        DriveFile(
                            id=raw["id"],
                            name=raw.get("name", "Untitled"),
                            mime_type=raw["mimeType"],
                            web_view_link=raw.get("webViewLink", ""),
                            size=size_int,
                        )
                    )
                    if len(files) >= self._max_files:
                        return files
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as exc:
            raise self._translate_http_error(exc, folder_id) from exc
        return files

    def _download_for_parsing_sync(
        self, file: DriveFile, credentials: Credentials
    ) -> tuple[bytes, str]:
        service = self._build(credentials)
        try:
            if file.mime_type == GOOGLE_DOC_MIME:
                request = service.files().export_media(
                    fileId=file.id, mimeType=TXT_MIME
                )
                return self._stream_download(request), TXT_MIME

            request = service.files().get_media(
                fileId=file.id, supportsAllDrives=True
            )
            return self._stream_download(request), file.mime_type
        except HttpError as exc:
            raise self._translate_http_error(exc, file.id) from exc

    @staticmethod
    def _stream_download(request) -> bytes:
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    @staticmethod
    def _translate_http_error(exc: HttpError, resource: str) -> Exception:
        status = getattr(getattr(exc, "resp", None), "status", None)
        logger.warning("Drive API error (status=%s) for '%s'", status, resource)
        if status == 404:
            return FolderNotFoundError()
        if status in (401, 403):
            return DrivePermissionError()
        return DriveApiError()
