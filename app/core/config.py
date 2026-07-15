"""
    we never want to expose our real secret key in the source code, so we will load it from an environment   variable
    The secrets include (JWT Secret Keys , Database Passwords, API Keys, etc.) and should be kept secret and not committed to version control.
"""
from pydantic_settings import BaseSettings , SettingsConfigDict

class Settings(BaseSettings): #template that will execute when the app starts and load the env variables into the app
    model_config = SettingsConfigDict(env_file=".env" , extra = "ignore" , env_file_encoding="utf-8")

#asynchronous database settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi" #this is the default database url for our app

#Auth
    JWT_SECRET_KEY: str = "my_secret key"
    JWT_ALGORITHM: str = "HS256" #specifically for hashing and signing the JWT tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8 

#Daraja API settings
    DARAJA_CONSUMER_KEY: str = "your_consumer_key"
    DARAJA_CONSUMER_SECRET: str = "your_consumer_secret"
    DARAJA_SHORTCODE: str = "your_shortcode"
    DARAJA_PASSKEY: str = "your_passkey"
    DARAJA_ENVIRONMENT: str = "sandbox"  # or "production"

# SMS GATEWAY & TARGETED BALANCE ALERT
    SMS_API_KEY: str = "your_sms_api_key"
    SMS_USERNAME: str = "your_sms_username"
    SMS_SENDER_ID: str = "your_sms_sender_id"

# BACKGROUND JOBS
    REDIS_URL: str = "redis://localhost:6379/0"  # Redis URL for background jobs

settings = Settings() #packages all the instructions into a single importable tool called settings  