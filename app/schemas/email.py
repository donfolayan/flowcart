from typing import Optional
from pydantic import BaseModel


class EmailSettings(BaseModel):
    provider: str
    host: Optional[str]
    port: int
    username: Optional[str]
    password: Optional[str]
    from_address: Optional[str]
    use_tls: bool
    use_ssl: bool
    timeout_seconds: int
    
class VerifyEmailRequest(BaseModel):
    token: str
    
class ResendVerificationRequest(BaseModel):
    email: str