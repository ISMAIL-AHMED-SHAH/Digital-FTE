"""Credential Manager Abstraction for Silver Tier.

Provides secure storage and retrieval of OAuth tokens using:
1. OS credential manager (Windows Credential Manager / macOS Keychain) via keyring
2. AES-256 encrypted file fallback for unsupported systems

Implements FR-021, FR-022, FR-023 from spec.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Service name prefix for keyring storage
SERVICE_PREFIX = "ai-employee"


class CredentialError(Exception):
    """Base exception for credential operations."""
    pass


class TokenExpiredError(CredentialError):
    """Token has expired and refresh failed."""
    pass


class TokenNotFoundError(CredentialError):
    """Token not found in storage."""
    pass


class CredentialStore(ABC):
    """Abstract base class for credential storage backends."""

    @abstractmethod
    def get(self, service: str, key: str) -> str | None:
        """Retrieve a credential value."""
        pass

    @abstractmethod
    def set(self, service: str, key: str, value: str) -> None:
        """Store a credential value."""
        pass

    @abstractmethod
    def delete(self, service: str, key: str) -> bool:
        """Delete a credential. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this storage backend is available."""
        pass


class KeyringStore(CredentialStore):
    """OS credential manager storage via keyring library."""

    def __init__(self):
        self._keyring = None
        self._available = None

    def _get_keyring(self):
        """Lazy import keyring to avoid import errors if not installed."""
        if self._keyring is None:
            try:
                import keyring
                self._keyring = keyring
            except ImportError:
                self._keyring = False
        return self._keyring if self._keyring else None

    def is_available(self) -> bool:
        """Check if keyring is available and functional."""
        if self._available is not None:
            return self._available

        kr = self._get_keyring()
        if not kr:
            self._available = False
            return False

        try:
            # Test if keyring backend is functional
            test_service = f"{SERVICE_PREFIX}-test"
            test_key = "availability-check"
            kr.set_password(test_service, test_key, "test")
            result = kr.get_password(test_service, test_key)
            kr.delete_password(test_service, test_key)
            self._available = result == "test"
        except Exception as e:
            logger.debug(f"Keyring not available: {e}")
            self._available = False

        return self._available

    def get(self, service: str, key: str) -> str | None:
        kr = self._get_keyring()
        if not kr:
            return None
        try:
            return kr.get_password(f"{SERVICE_PREFIX}-{service}", key)
        except Exception as e:
            logger.warning(f"Failed to get credential from keyring: {e}")
            return None

    def set(self, service: str, key: str, value: str) -> None:
        kr = self._get_keyring()
        if not kr:
            raise CredentialError("Keyring not available")
        try:
            kr.set_password(f"{SERVICE_PREFIX}-{service}", key, value)
        except Exception as e:
            raise CredentialError(f"Failed to store credential in keyring: {e}")

    def delete(self, service: str, key: str) -> bool:
        kr = self._get_keyring()
        if not kr:
            return False
        try:
            kr.delete_password(f"{SERVICE_PREFIX}-{service}", key)
            return True
        except Exception:
            return False


class EncryptedFileStore(CredentialStore):
    """AES-256 encrypted file storage fallback.

    Uses machine-specific key derived from hostname and username.
    """

    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir or Path.home() / ".ai-employee" / "credentials"
        self._fernet = None
        self._available = None

    def _get_fernet(self):
        """Get or create Fernet encryption instance."""
        if self._fernet is None:
            try:
                from cryptography.fernet import Fernet
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

                # Derive key from machine-specific data
                import socket
                machine_id = f"{socket.gethostname()}-{os.getlogin()}-ai-employee"
                salt = b"ai-employee-salt-v1"  # Fixed salt for consistency

                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=480000,
                )
                key = b64encode(kdf.derive(machine_id.encode()))
                self._fernet = Fernet(key)
            except ImportError:
                self._fernet = False
            except Exception as e:
                logger.warning(f"Failed to initialize encryption: {e}")
                self._fernet = False

        return self._fernet if self._fernet else None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        self._available = self._get_fernet() is not None
        return self._available

    def _get_file_path(self, service: str, key: str) -> Path:
        """Get the file path for a credential."""
        safe_name = f"{service}_{key}".replace("/", "_").replace("\\", "_")
        return self._storage_dir / f"{safe_name}.enc"

    def get(self, service: str, key: str) -> str | None:
        fernet = self._get_fernet()
        if not fernet:
            return None

        file_path = self._get_file_path(service, key)
        if not file_path.exists():
            return None

        try:
            encrypted_data = file_path.read_bytes()
            decrypted = fernet.decrypt(encrypted_data)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to decrypt credential file: {e}")
            return None

    def set(self, service: str, key: str, value: str) -> None:
        fernet = self._get_fernet()
        if not fernet:
            raise CredentialError("Encryption not available")

        file_path = self._get_file_path(service, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            encrypted = fernet.encrypt(value.encode("utf-8"))
            file_path.write_bytes(encrypted)
            # Set restrictive permissions on Unix
            if os.name != "nt":
                file_path.chmod(0o600)
        except Exception as e:
            raise CredentialError(f"Failed to write encrypted credential: {e}")

    def delete(self, service: str, key: str) -> bool:
        file_path = self._get_file_path(service, key)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False


class CredentialManager:
    """Unified credential manager with automatic backend selection.

    Usage:
        creds = CredentialManager()

        # Store OAuth token
        creds.store_token("gmail", {
            "access_token": "...",
            "refresh_token": "...",
            "expires_at": "2026-01-25T12:00:00Z"
        })

        # Retrieve token
        token = creds.get_token("gmail")

        # Check if refresh needed
        if creds.is_token_expired("gmail"):
            new_token = refresh_oauth_token(token["refresh_token"])
            creds.store_token("gmail", new_token)
    """

    def __init__(self, encrypted_fallback_dir: Path | None = None):
        """Initialize credential manager with available backends.

        Args:
            encrypted_fallback_dir: Optional custom directory for encrypted file storage
        """
        self._keyring = KeyringStore()
        self._encrypted = EncryptedFileStore(encrypted_fallback_dir)
        self._primary_store: CredentialStore | None = None

        # Select primary store
        if self._keyring.is_available():
            self._primary_store = self._keyring
            logger.info("Using OS credential manager (keyring)")
        elif self._encrypted.is_available():
            self._primary_store = self._encrypted
            logger.info("Using encrypted file storage (fallback)")
        else:
            logger.warning("No secure credential storage available!")

    def is_available(self) -> bool:
        """Check if any credential storage is available."""
        return self._primary_store is not None

    def get_token(self, service: str) -> dict[str, Any] | None:
        """Retrieve an OAuth token for a service.

        Args:
            service: Service name (e.g., "gmail", "linkedin")

        Returns:
            Token dictionary with access_token, refresh_token, expires_at, etc.
            None if not found.
        """
        if not self._primary_store:
            raise CredentialError("No credential storage available")

        token_json = self._primary_store.get(service, "oauth_token")
        if not token_json:
            return None

        try:
            return json.loads(token_json)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid token format for {service}: {e}")
            return None

    def store_token(self, service: str, token: dict[str, Any]) -> None:
        """Store an OAuth token for a service.

        Args:
            service: Service name (e.g., "gmail", "linkedin")
            token: Token dictionary with at minimum access_token
        """
        if not self._primary_store:
            raise CredentialError("No credential storage available")

        # Ensure expires_at is set if not present
        if "expires_at" not in token and "expires_in" in token:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token["expires_in"])
            token["expires_at"] = expires_at.isoformat()

        token_json = json.dumps(token)
        self._primary_store.set(service, "oauth_token", token_json)
        logger.info(f"Stored token for {service}")

    def delete_token(self, service: str) -> bool:
        """Delete an OAuth token for a service.

        Args:
            service: Service name

        Returns:
            True if deleted, False if not found
        """
        if not self._primary_store:
            return False

        return self._primary_store.delete(service, "oauth_token")

    def is_token_expired(self, service: str, buffer_seconds: int = 300) -> bool:
        """Check if a token is expired or will expire soon.

        Args:
            service: Service name
            buffer_seconds: Consider expired if expiring within this many seconds

        Returns:
            True if expired or expiring soon, False otherwise
        """
        token = self.get_token(service)
        if not token:
            return True

        expires_at_str = token.get("expires_at")
        if not expires_at_str:
            # No expiration info, assume valid
            return False

        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            buffer = timedelta(seconds=buffer_seconds)
            return datetime.now(timezone.utc) + buffer >= expires_at
        except (ValueError, TypeError):
            logger.warning(f"Invalid expires_at format for {service}")
            return False

    def refresh_token(
        self,
        service: str,
        refresh_callback: callable,
        max_retries: int = 3
    ) -> dict[str, Any]:
        """Refresh an OAuth token using the provided callback.

        Args:
            service: Service name
            refresh_callback: Function that takes refresh_token and returns new token dict
            max_retries: Maximum refresh attempts

        Returns:
            New token dictionary

        Raises:
            TokenExpiredError: If refresh fails after all retries
            TokenNotFoundError: If no token exists to refresh
        """
        token = self.get_token(service)
        if not token:
            raise TokenNotFoundError(f"No token found for {service}")

        refresh_token_value = token.get("refresh_token")
        if not refresh_token_value:
            raise TokenExpiredError(f"No refresh token available for {service}")

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Refreshing token for {service} (attempt {attempt + 1}/{max_retries})")
                new_token = refresh_callback(refresh_token_value)

                # Preserve refresh_token if not returned
                if "refresh_token" not in new_token and refresh_token_value:
                    new_token["refresh_token"] = refresh_token_value

                self.store_token(service, new_token)
                logger.info(f"Successfully refreshed token for {service}")
                return new_token

            except Exception as e:
                last_error = e
                logger.warning(f"Token refresh attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff

        raise TokenExpiredError(
            f"Failed to refresh token for {service} after {max_retries} attempts: {last_error}"
        )


# Module-level convenience instance
_default_manager: CredentialManager | None = None


def get_credential_manager() -> CredentialManager:
    """Get the default credential manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = CredentialManager()
    return _default_manager


def get_token(service: str) -> dict[str, Any] | None:
    """Convenience function to get a token using default manager."""
    return get_credential_manager().get_token(service)


def store_token(service: str, token: dict[str, Any]) -> None:
    """Convenience function to store a token using default manager."""
    get_credential_manager().store_token(service, token)


def refresh_token(service: str, refresh_callback: callable, max_retries: int = 3) -> dict[str, Any]:
    """Convenience function to refresh a token using default manager."""
    return get_credential_manager().refresh_token(service, refresh_callback, max_retries)
