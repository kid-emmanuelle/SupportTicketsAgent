import os
from dotenv import load_dotenv
import snowflake.connector
from cryptography.hazmat.primitives import serialization


def load_private_key(private_key_path: str) -> bytes:
    """
    Load a PEM private key and return it in DER format
    (required by Snowflake connector).
    """
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connect_snowflake():
    """
    Create and return a Snowflake connection using key pair authentication.
    """
    load_dotenv()

    private_key = load_private_key(
        os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    )

    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        private_key=private_key,
        ocsp_fail_open=True,
    )

    return conn
