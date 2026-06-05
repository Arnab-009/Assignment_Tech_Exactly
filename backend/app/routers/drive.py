"""Google Drive listing routes."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials

from app.dependencies import get_current_credentials, get_drive_service
from app.exceptions import InvalidFolderIdError
from app.models.schemas import DriveFile, DriveFolder
from app.services.drive_service import DriveService

router = APIRouter(prefix="/api/drive", tags=["drive"])

_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,200}$")


@router.get("/folders", response_model=list[DriveFolder])
async def list_folders(
    credentials: Credentials = Depends(get_current_credentials),
    drive: DriveService = Depends(get_drive_service),
) -> list[DriveFolder]:
    """Return all Drive folders visible to the authenticated user."""
    return await drive.list_folders(credentials)


@router.get("/files", response_model=list[DriveFile])
async def list_files(
    folder_id: str = Query(..., min_length=10, max_length=200),
    credentials: Credentials = Depends(get_current_credentials),
    drive: DriveService = Depends(get_drive_service),
) -> list[DriveFile]:
    """Return the supported documents inside a Drive folder."""
    return await drive.list_files(folder_id, credentials)


@router.get("/preview/{file_id}")
def preview(
    file_id: str,
    _credentials: Credentials = Depends(get_current_credentials),
) -> RedirectResponse:
    """Redirect to the file's Google Drive viewer (authenticated users only)."""
    if not _DRIVE_ID_RE.match(file_id):
        raise InvalidFolderIdError("Invalid file ID.")
    return RedirectResponse(f"https://drive.google.com/file/d/{file_id}/view")
