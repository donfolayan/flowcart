from pydantic import BaseModel, EmailStr, Field

class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user requesting password reset")
    
class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset token sent to the user's email")
    new_password: str = Field(..., min_length=8, description="New password for the user")