"""
Compatibility shim: older fix files imported `chrono_chain.core.*`.
They now resolve to the real `chronochain` package.
"""
from chronochain import *  # noqa: F401,F403
from chronochain.core import schema, normalize  # noqa: F401
