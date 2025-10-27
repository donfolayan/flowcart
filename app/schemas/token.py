from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="Access token for the user")
    refresh_token: str = Field(..., description="Refresh token for the user")
    token_type: str = Field("bearer", description="Type of the token")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token for the user")
