"""
    Database engine and session management / Factory for the application
    Tenant-scopped session logic ( setting for RLS context variables ) livs in app/middlewares/tenant.py , not here
    This file is literally "dump plumbing code" , so its obvious where to look for the security critical part
"""


