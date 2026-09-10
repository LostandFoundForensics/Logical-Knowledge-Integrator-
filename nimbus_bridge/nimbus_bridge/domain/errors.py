from __future__ import annotations


class NimbusBridgeError(Exception):
    """Base class for all Nimbus Bridge errors."""


class ScopeValidationError(NimbusBridgeError):
    pass


class ProviderNotRecognizedError(NimbusBridgeError):
    pass


class ManifestIntegrityError(NimbusBridgeError):
    pass


class VaultIOError(NimbusBridgeError):
    pass
