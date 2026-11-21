"""Customer routes (docs/design/06_API_CONTRACT.md, Customers). HTTP only; rules in the service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.repositories.base import MAX_PAGE_SIZE
from app.schemas.customer import CustomerDetail, CustomerPage
from app.services import customer_service

router = APIRouter(
    prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)]
)

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=CustomerPage)
async def list_customers(
    session: Session,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> CustomerPage:
    return await customer_service.list_customers(
        session, search=search, page=page, page_size=page_size
    )


@router.get("/{customer_id}", response_model=CustomerDetail)
async def get_customer(customer_id: str, session: Session) -> CustomerDetail:
    try:
        return await customer_service.get_customer(session, customer_id)
    except customer_service.CustomerNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found") from None
