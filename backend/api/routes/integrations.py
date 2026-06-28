from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, List
from pydantic import BaseModel

from backend.db.models.user import User
from backend.db.models.third_party_integration import ThirdPartyIntegration
from backend.db.models.third_party_user_account import ThirdPartyUserAccount
from backend.api.deps import get_db, get_current_user
from backend.utils.encryption import encrypt_token

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class IntegrationResponse(BaseModel):
    name: str
    display_name: str
    description: str | None
    logo_url: str | None
    is_connected: bool


class ConnectRequest(BaseModel):
    access_token: str


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Any:
    """List all available integrations and whether the user is connected to them."""
    # Get all enabled integrations
    stmt = select(ThirdPartyIntegration).where(ThirdPartyIntegration.is_enabled == True)
    result = await db.execute(stmt)
    integrations = result.scalars().all()

    # Get the user's connected integrations
    stmt_accounts = select(ThirdPartyUserAccount.integration_id).where(
        ThirdPartyUserAccount.user_id == current_user.id,
        ThirdPartyUserAccount.is_active == True,
    )
    result_accounts = await db.execute(stmt_accounts)
    connected_ids = set(result_accounts.scalars().all())

    response = []
    for inc in integrations:
        response.append(
            {
                "name": inc.name,
                "display_name": inc.display_name,
                "description": inc.description,
                "logo_url": inc.logo_url,
                "is_connected": inc.id in connected_ids,
            }
        )
    return response


@router.post("/{name}/pat")
async def connect_integration_pat(
    name: str,
    req: ConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Connect a third-party integration using a Personal Access Token."""
    # Find integration
    stmt = select(ThirdPartyIntegration).where(ThirdPartyIntegration.name == name)
    integration = (await db.execute(stmt)).scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if already connected
    stmt_acc = select(ThirdPartyUserAccount).where(
        ThirdPartyUserAccount.user_id == current_user.id,
        ThirdPartyUserAccount.integration_id == integration.id,
    )
    account = (await db.execute(stmt_acc)).scalar_one_or_none()

    encrypted = encrypt_token(req.access_token)

    if account:
        account.access_token_encrypted = encrypted
        account.is_active = True
    else:
        account = ThirdPartyUserAccount(
            user_id=current_user.id,
            integration_id=integration.id,
            access_token_encrypted=encrypted,
            credentials={},
        )
        db.add(account)

    await db.commit()
    return {"message": f"Successfully connected to {integration.display_name}"}


@router.delete("/{name}")
async def disconnect_integration(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Disconnect a third-party integration."""
    stmt = select(ThirdPartyIntegration).where(ThirdPartyIntegration.name == name)
    integration = (await db.execute(stmt)).scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    stmt_acc = select(ThirdPartyUserAccount).where(
        ThirdPartyUserAccount.user_id == current_user.id,
        ThirdPartyUserAccount.integration_id == integration.id,
    )
    account = (await db.execute(stmt_acc)).scalar_one_or_none()

    if account:
        await db.delete(account)
        await db.commit()

    return {"message": f"Successfully disconnected from {integration.display_name}"}
