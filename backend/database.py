import os
from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


CONNECTION_STRING = os.getenv(
    "SQLSERVER_CONNECTION_STRING",
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=LAPTOP-9S16DEOO;"
    "DATABASE=MultiServiceDB;"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;",
)

engine = create_engine(
    URL.create("mssql+pyodbc", query={"odbc_connect": CONNECTION_STRING}),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
