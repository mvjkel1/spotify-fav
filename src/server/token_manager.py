class TokenManager:
    def __init__(self):
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    def set_tokens(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token

    def get_tokens(self):
        return self.access_token, self.refresh_token

    def clear_tokens(self):
        self.access_token = None
        self.refresh_token = None


token_manager = TokenManager()
