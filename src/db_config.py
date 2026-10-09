import os

from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


project_dir = Path(__file__).resolve().parent.parent

env_file = project_dir / ".env"

if not env_file.exists():
    raise FileNotFoundError(
        f"Environment file not found: {env_file}"
    )

load_dotenv(env_file)


db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")


required_variables = {
    "DB_USER": db_user,
    "DB_PASSWORD": db_password,
    "DB_HOST": db_host,
    "DB_PORT": db_port,
    "DB_NAME": db_name
}

missing_variables = [
    name
    for name, value in required_variables.items()
    if not value
]

if missing_variables:
    raise ValueError(
        "Missing required environment variable(s): "
        + ", ".join(missing_variables)
    )


connection_url = URL.create(
    drivername="postgresql+psycopg2",
    username=db_user,
    password=db_password,
    host=db_host,
    port=int(db_port),
    database=db_name
)

engine = create_engine(
    connection_url,
    pool_pre_ping=True
)