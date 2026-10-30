import os

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr

from app.auth import create_access_token, get_current_advisor, verify_password
from app.db.db import get_connection

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
	email: EmailStr
	password: str


@router.post("/login")
def login(credentials: LoginRequest, response: Response):
	with get_connection() as conn, conn.cursor() as cur:
		cur.execute(
			"SELECT id, password_hash FROM advisors WHERE lower(email) = lower(%s)",
			(str(credentials.email),),
		)
		advisor = cur.fetchone()

	if advisor is None or not verify_password(credentials.password, advisor[1]):
		raise HTTPException(status_code=401, detail="Invalid email or password.")

	try:
		token = create_access_token(advisor[0])
	except RuntimeError:
		raise HTTPException(
			status_code=503,
			detail="Authentication is not configured.",
		) from None

	response.set_cookie(
		key="orbit_session",
		value=token,
		max_age=3600,
		httponly=True,
		secure=os.environ.get("ORBIT_COOKIE_SECURE", "false").lower() == "true",
		samesite="lax",
		path="/",
	)
	return {
		"expires_in": 3600,
		"advisor": {"id": advisor[0], "email": str(credentials.email)},
	}


@router.get("/me")
def current_session(advisor: dict[str, int] = Depends(get_current_advisor)):
	return advisor


@router.post("/logout")
def logout(response: Response):
	response.delete_cookie("orbit_session", path="/")
	return {"message": "Signed out."}
