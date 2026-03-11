"""
Glean Action Server - Natural Language to JQL Converter

This package implements a Glean Action Server that converts natural language
queries into valid Jira JQL (Jira Query Language) and validates them
against Jira's REST API.

Usage:
    python main.py action-server
"""

from actions.server import run_server

__all__ = ["run_server"]
