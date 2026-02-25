# Changelog

> **Last updated:** 2026-02-24

All notable changes to the Flask Server project are documented in this file. This project tracks the complete rewrite of the original Node.js server application into Python 3 using the Flask web framework, preserving all original functionalities.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-24

### Added

- Initial Flask application scaffold built on Python 3 with Flask 3.1.x, establishing the foundation for the complete server rewrite from Node.js
- Project documentation structure powered by MkDocs with the Material theme, providing a fully navigable documentation site with search and responsive layout
- REST API endpoint framework using Flask blueprints, organizing routes into modular, maintainable groups that mirror the original Express.js route structure
- SQLAlchemy ORM integration via Flask-SQLAlchemy for robust, Pythonic database access replacing the original Node.js database layer
- Flask-Migrate for Alembic-based database schema migrations, enabling version-controlled database changes with upgrade and downgrade support
- Flask-CORS for Cross-Origin Resource Sharing configuration, preserving the same CORS policies from the original Node.js server
- Authentication and authorization middleware implemented through Flask before-request hooks and decorators, replacing Express.js middleware patterns
- Configuration management with python-dotenv for environment variable loading, supporting development, staging, and production configuration profiles
- Comprehensive test suite structure using pytest and the Flask test client, covering unit tests, integration tests, and API endpoint tests
- Production deployment support with Gunicorn as the WSGI HTTP server, including Docker containerization and reverse proxy configuration guides
- Architecture documentation featuring Mermaid diagrams for system overview, request lifecycle, and data flow visualization
- Node.js to Flask migration guide mapping Express.js patterns to Flask equivalents, including route definitions, middleware chains, async handling, and package substitutions
- API reference documentation cataloging all REST endpoints with HTTP methods, URL patterns, request and response schemas, status codes, and example payloads
- Getting started guides covering installation of Python 3 and Flask dependencies, environment configuration with sample `.env` files, and a quickstart walkthrough for first server run

### Changed

- Complete rewrite of the server application from Node.js with Express.js to Python 3 with Flask 3.1.x, replacing the entire runtime, framework, package ecosystem, and deployment toolchain while maintaining full feature parity with the original implementation

### Migration Notes

- All original Node.js server functionalities have been preserved in the Flask implementation, including REST API endpoints, authentication flows, database operations, CORS handling, error responses, and middleware behavior
- Express.js route handlers have been translated to Flask blueprint view functions with equivalent URL rules, HTTP method handling, and request/response processing
- Node.js npm packages have been replaced with Python pip equivalents: Express → Flask, cors → Flask-CORS, Sequelize/Mongoose → Flask-SQLAlchemy, jsonwebtoken → PyJWT, dotenv → python-dotenv, Jest/Mocha → pytest
- For a detailed mapping of Node.js concepts to Flask equivalents, including code examples and pattern translations, refer to the [Migration Guide](docs/guides/migration-from-nodejs.md)
