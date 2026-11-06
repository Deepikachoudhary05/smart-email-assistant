from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.gmail_service import gmail_service
from app.models.email_model import Email, Draft

router = APIRouter(prefix="/api/emails", tags=["emails"])


# Pydantic models for request/response
class EmailResponse(BaseModel):
    id: str
    sender: str
    subject: str
    body: str


class DraftCreateRequest(BaseModel):
    email_id: int
    recipient_email: str
    subject: str
    body: str


class DraftResponse(BaseModel):
    id: int
    email_id: int
    recipient_email: str
    subject: str
    body: str
    analysis: Optional[str] = None


@router.get("/fetch")
async def fetch_emails():
    """
    Fetch unread emails from Gmail and save to database
    """
    try:
        # Get emails from Gmail
        emails = gmail_service.get_emails(query='is:unread', max_results=10)

        saved_count = 0
        for email_data in emails:
            email = Email(
                gmail_id=email_data['id'],
                sender=email_data['sender'],
                subject=email_data['subject'],
                body=email_data['body']
            )
            email_id = email.save()
            if email_id:
                saved_count += 1

        return {
            'status': 'success',
            'fetched': len(emails),
            'saved': saved_count,
            'emails': emails
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_emails():
    """
    Get all emails from database
    """
    try:
        emails = Email.get_all()
        return {
            'status': 'success',
            'count': len(emails),
            'emails': emails
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{email_id}")
async def get_email(email_id: int):
    """
    Get specific email by ID
    """
    try:
        email = Email.get_by_id(email_id)
        if not email:
            raise HTTPException(status_code=404, detail='Email not found')

        return {
            'status': 'success',
            'email': email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts/list")
async def list_drafts():
    """
    Get all drafts from database
    """
    try:
        drafts = Draft.get_all()
        return {
            'status': 'success',
            'count': len(drafts),
            'drafts': drafts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts/{email_id}")
async def get_email_drafts(email_id: int):
    """
    Get all drafts for a specific email
    """
    try:
        drafts = Draft.get_by_email_id(email_id)
        return {
            'status': 'success',
            'count': len(drafts),
            'drafts': drafts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/create")
async def create_draft(request: DraftCreateRequest):
    """
    Create a draft in Gmail and save to database
    """
    try:
        # Create draft in Gmail
        gmail_draft = gmail_service.create_draft(
            request.recipient_email,
            request.subject,
            request.body
        )

        if not gmail_draft:
            raise HTTPException(status_code=500, detail='Failed to create draft in Gmail')

        # Save to database
        draft = Draft(
            email_id=request.email_id,
            recipient_email=request.recipient_email,
            subject=request.subject,
            body=request.body
        )
        draft_id = draft.save()

        return {
            'status': 'success',
            'draft_id': draft_id,
            'gmail_draft_id': gmail_draft.get('id'),
            'message': 'Draft created successfully!'
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))