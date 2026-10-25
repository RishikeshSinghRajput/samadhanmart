import getpass
import hashlib
import secrets


def main() -> None:
    password = getpass.getpass("New admin password (12+ characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    print(f"PasswordHash: pbkdf2_sha256$310000${salt.hex()}${digest.hex()}")


if __name__ == "__main__":
    main()
