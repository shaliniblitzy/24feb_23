"""Shared utilities package for the Flask backend application.

This package provides foundational utility functions and decorators used across
the application's services, middleware, routes, and repositories:

- logging: Structured JSON logging with request ID correlation and CloudWatch compatibility
- retry: Retry with backoff decorators for resilient external service calls
"""
