# Database Guide

*Last updated: 2026-02-24*

This guide provides a comprehensive walkthrough of database integration in the Flask server application, covering ORM setup with Flask-SQLAlchemy, schema migration with Flask-Migrate, query patterns, relationship handling, and connection management. It is intended for developers working with the data layer of the Flask application, including defining models, writing queries, and managing database migrations.

## Database Overview

The Flask server uses a relational database accessed through the following stack:

- **Flask-SQLAlchemy** (v3.1.1) — SQLAlchemy ORM integration for Flask, providing the `db.Model` base class, session management, and query interface for all database operations.
- **Flask-Migrate** (v4.0.7) — Database migration framework built on Alembic that provides Flask-aware CLI commands (`flask db`) for generating and applying schema changes.
- **SQLAlchemy** — The underlying Python SQL toolkit and Object-Relational Mapper, provided transitively by Flask-SQLAlchemy. SQLAlchemy handles connection pooling, SQL generation, and the unit-of-work pattern for tracking changes.

The application follows the **ORM (Object-Relational Mapping) pattern**: Python classes (called models) map to database tables, and object instances map to individual table rows. Developers interact with data through Python objects and method calls rather than writing raw SQL.

See [Architecture Overview](../architecture/overview.md) for the system's layered architecture and where the database layer fits.

## Database Configuration

All database settings are controlled through environment variables, loaded via `python-dotenv` and accessed through Flask's configuration system. The following table catalogs every database-related configuration option:

| Variable | Description | Default | Required |
|---|---|---|---|
| `DATABASE_URL` | Full database connection URI | `sqlite:///app.db` | Yes (production) |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | Track object modifications and emit signals | `False` | No |
| `SQLALCHEMY_ECHO` | Log all SQL statements to the application logger | `False` | No |
| `SQLALCHEMY_POOL_SIZE` | Number of persistent connections in the pool | `5` | No |
| `SQLALCHEMY_POOL_TIMEOUT` | Seconds to wait for a connection from the pool | `30` | No |
| `SQLALCHEMY_MAX_OVERFLOW` | Maximum connections allowed above `pool_size` | `10` | No |

### Configuration Class

Define database configuration in the application's configuration module:

```python
# config.py
import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "false").lower() == "true"
```

### Connection URI Examples

The `DATABASE_URL` environment variable accepts standard SQLAlchemy connection URIs. Below are examples for the most common database engines:

```bash
# SQLite (development)
DATABASE_URL=sqlite:///app.db

# PostgreSQL (production recommended)
DATABASE_URL=postgresql://user:password@localhost:5432/flaskdb

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/flaskdb
```

> **Note:** For production deployments, PostgreSQL is recommended. SQLite is suitable only for local development and testing due to its limited concurrency support.

## Flask-SQLAlchemy Setup

Flask-SQLAlchemy and Flask-Migrate are initialized using the **deferred initialization** pattern. Extensions are created as module-level instances in a dedicated `extensions.py` file, then bound to the Flask application inside the application factory function. This pattern allows multiple modules to import the shared `db` and `migrate` instances without requiring the Flask app to exist at import time.

### Extension Initialization

```python
# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
```

### Application Factory Integration

```python
# app.py
from flask import Flask
from extensions import db, migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from routes.users import users_bp
    app.register_blueprint(users_bp, url_prefix="/api/users")

    return app
```

The `db.init_app(app)` call binds the SQLAlchemy instance to the Flask application, enabling session management and query execution within the application context. The `migrate.init_app(app, db)` call registers the Flask-Migrate CLI commands (`flask db init`, `flask db migrate`, `flask db upgrade`) with the application.

## Defining Models

Models are SQLAlchemy ORM classes that map to database tables. Each model inherits from `db.Model`, declares a `__tablename__`, and defines columns using `db.Column`. The example below demonstrates all commonly used column types, constraints, and a serialization method:

```python
# models/user.py
from extensions import db
from datetime import datetime, timezone

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f"<User {self.email}>"
```

### Common Column Types

| SQLAlchemy Type | Python Type | Description |
|---|---|---|
| `db.Integer` | `int` | Integer values; used for primary keys, foreign keys, and counters |
| `db.String(n)` | `str` | Variable-length string with a maximum of `n` characters |
| `db.Text` | `str` | Unlimited-length text; suitable for descriptions and long content |
| `db.Boolean` | `bool` | True/false flags |
| `db.DateTime` | `datetime` | Date and time values; store in UTC for consistency |
| `db.Float` | `float` | Floating-point decimal numbers |
| `db.JSON` | `dict` / `list` | Structured JSON data stored natively (supported by PostgreSQL and SQLite 3.9+) |

### Column Options

| Option | Type | Description |
|---|---|---|
| `primary_key` | `bool` | Marks the column as the table's primary key; enables auto-increment for integer columns |
| `unique` | `bool` | Enforces a database-level UNIQUE constraint preventing duplicate values |
| `nullable` | `bool` | When `False`, adds a NOT NULL constraint; the column must always have a value |
| `default` | value or callable | Sets the default value for new records; callables are invoked at insert time |
| `index` | `bool` | Creates a database index on the column to accelerate lookups and filters |
| `onupdate` | value or callable | Sets the value automatically when the row is updated; useful for `updated_at` timestamps |

See [Models Reference](../api-reference/models.md) for the complete data model catalog.

## Relationships

SQLAlchemy supports declarative relationship definitions between models using `db.relationship()` and `db.ForeignKey()`. Relationships enable navigation between related objects through Python attributes rather than manual join queries.

### One-to-Many Relationship

A one-to-many relationship connects a parent model to multiple child models. The foreign key is defined on the child (the "many" side), and the parent declares the relationship with a `backref` that creates the reverse accessor on the child:

```python
# models/user.py
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    posts = db.relationship("Post", backref="author", lazy="select")

# models/post.py
class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
```

With this relationship defined, you can access a user's posts via `user.posts` (returns a list of `Post` instances) and a post's author via `post.author` (returns the `User` instance).

### Many-to-Many Relationship

A many-to-many relationship requires an association table that stores the pairs of foreign keys linking the two models. Neither model directly holds a foreign key to the other:

```python
# Association table
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
)

class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    users = db.relationship("User", secondary=user_roles, backref="roles")
```

With this setup, `role.users` returns all users assigned to that role, and `user.roles` returns all roles assigned to that user.

### Lazy Loading Options

The `lazy` parameter on `db.relationship()` controls when and how related objects are loaded from the database:

| Value | Behavior |
|---|---|
| `"select"` | (Default) Related objects are loaded on first access via a separate SELECT query |
| `"joined"` | Related objects are loaded in the same query as the parent using a SQL JOIN |
| `"subquery"` | Related objects are loaded using a subquery; efficient for collections |
| `"dynamic"` | Returns a query object instead of a list; useful for large collections that need filtering |

Choose `"joined"` or `"subquery"` when you know the related data will always be needed (reduces the number of queries). Use `"select"` (default) or `"dynamic"` when related data is accessed conditionally or when the collection is large.

## Query Patterns

Flask-SQLAlchemy provides a `query` interface on every model class and direct access to the SQLAlchemy session via `db.session`. The following sections demonstrate common query patterns used throughout the application.

### Basic Queries

```python
# Get all records
users = User.query.all()

# Get by primary key
user = User.query.get(1)
# Or using Flask-SQLAlchemy 3.x recommended pattern:
user = db.session.get(User, 1)

# Get or return 404
user = User.query.get_or_404(1)

# Filter by column value
admins = User.query.filter_by(role="admin").all()

# Filter with expressions
active_users = User.query.filter(User.is_active == True).all()
```

### Advanced Queries

```python
# Chaining filters
results = User.query.filter(
    User.role == "user",
    User.is_active == True,
).order_by(User.created_at.desc()).all()

# Pagination
page = User.query.paginate(page=1, per_page=20, error_out=False)
users = page.items  # List of User instances
total = page.total  # Total number of records

# Count
user_count = User.query.filter_by(is_active=True).count()

# First result or None
user = User.query.filter_by(email="user@example.com").first()

# Exists check
exists = db.session.query(
    User.query.filter_by(email="user@example.com").exists()
).scalar()
```

### Creating and Updating Records

```python
# Create
new_user = User(email="new@example.com", name="New User", password_hash=hashed)
db.session.add(new_user)
db.session.commit()

# Update
user = User.query.get_or_404(user_id)
user.name = "Updated Name"
user.updated_at = datetime.now(timezone.utc)
db.session.commit()

# Delete
user = User.query.get_or_404(user_id)
db.session.delete(user)
db.session.commit()
```

> **Important:** Always call `db.session.commit()` after making changes. If an error occurs, call `db.session.rollback()` to revert uncommitted changes and prevent the session from entering an inconsistent state.

## Database Migrations

Flask-Migrate wraps [Alembic](https://alembic.sqlalchemy.org/) to provide Flask-aware CLI commands for managing database schema changes. Migrations are versioned scripts that track schema evolution, enabling reproducible upgrades and rollbacks across development, staging, and production environments.

### Initialize Migrations

Run this command once when setting up the project for the first time. It creates a `migrations/` directory containing Alembic configuration and a `versions/` subdirectory for migration scripts:

```bash
# Initialize the migrations directory (one-time setup)
flask db init
```

### Create a Migration

After modifying model definitions (adding columns, creating new tables, changing constraints), generate a migration script. Flask-Migrate compares the current database schema with the ORM model definitions and auto-generates the migration:

```bash
# Auto-generate a migration from model changes
flask db migrate -m "Add users table"
```

Always review the generated migration script in `migrations/versions/` before applying it. Auto-generated migrations may miss certain changes (such as table or column renames) that require manual adjustment.

### Apply Migrations

```bash
# Apply all pending migrations
flask db upgrade

# Downgrade by one revision
flask db downgrade

# Show current migration revision
flask db current

# Show migration history
flask db history
```

### Migration Best Practices

- **Always review auto-generated migration scripts** before applying them. Verify that the generated `upgrade()` and `downgrade()` functions accurately reflect your intended changes.
- **Add descriptive messages** to every migration using the `-m` flag (for example, `flask db migrate -m "Add email index to users table"`). Descriptive messages make it easy to identify the purpose of each migration in the history.
- **Test migrations on a copy of the production database** before applying to production. Run `flask db upgrade` against a staging database to verify the migration completes without errors or data loss.
- **Never edit migration files after they have been applied** to shared databases (staging, production). If a correction is needed, create a new migration that applies the fix.
- **Commit migration files to version control.** The `migrations/versions/` directory must be tracked in Git so that all team members and deployment pipelines use the same migration history.

## Connection Pooling

SQLAlchemy maintains a pool of database connections that are reused across requests, avoiding the overhead of establishing a new connection for every query. Proper pool configuration is critical for production performance and stability.

### Pool Configuration

Configure connection pool parameters through the `SQLALCHEMY_ENGINE_OPTIONS` dictionary in your production configuration class:

```python
class ProductionConfig(Config):
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "max_overflow": 20,
    }
```

### Pool Parameters

| Parameter | Default | Description |
|---|---|---|
| `pool_size` | `5` | Number of persistent connections maintained in the pool. These connections remain open and are reused across requests. |
| `pool_timeout` | `30` | Seconds to wait when requesting a connection from the pool. If no connection becomes available within this time, a `TimeoutError` is raised. |
| `pool_recycle` | `-1` (disabled) | Seconds after which a connection is automatically recycled (closed and reopened). Set to `1800` (30 minutes) to prevent stale connections, especially with MySQL which closes idle connections after `wait_timeout`. |
| `max_overflow` | `10` | Number of additional connections allowed above `pool_size` during peak load. These overflow connections are closed immediately after use. The total maximum concurrent connections is `pool_size + max_overflow`. |

### Sizing Guidelines

- **Development:** Use defaults (`pool_size=5`, `max_overflow=10`). SQLite ignores pool settings since it uses file-based locking.
- **Production:** Set `pool_size` to match your expected number of concurrent request-handling workers. For a Gunicorn deployment with 4 workers, a `pool_size` of 5–10 per worker is typical.
- **High traffic:** Increase `max_overflow` to handle traffic bursts without rejecting requests. Monitor pool exhaustion using SQLAlchemy's pool events or database server connection metrics.

## Troubleshooting

The following table lists common database issues, their causes, and recommended solutions:

| Issue | Cause | Solution |
|---|---|---|
| `OperationalError: no such table` | Migrations not applied | Run `flask db upgrade` to apply pending migrations |
| `IntegrityError: UNIQUE constraint failed` | Duplicate value in unique column | Check for existing records before insert; handle the exception in the service layer |
| `TimeoutError: QueuePool limit reached` | Connection pool exhausted | Increase `pool_size` and `max_overflow`; ensure sessions are closed after use |
| `DetachedInstanceError` | Accessing lazy-loaded attribute outside session | Use eager loading (for example, `joinedload`) or access the attribute within the session scope |
| Migrations out of sync | Model changes not reflected in database | Run `flask db migrate` to generate a new migration, then `flask db upgrade` to apply it |
| `Multiple heads` in migration history | Concurrent migration branches created by different developers | Merge heads with `flask db merge heads`, then apply the merged migration |
| `ModuleNotFoundError: flask_sqlalchemy` | Flask-SQLAlchemy not installed | Install with `pip install flask-sqlalchemy==3.1.1` |
| `ModuleNotFoundError: flask_migrate` | Flask-Migrate not installed | Install with `pip install flask-migrate==4.0.7` |

## See Also

- [Models Reference](../api-reference/models.md) — Complete data model catalog with field types, constraints, and relationships
- [Data Flow](../architecture/data-flow.md) — How data moves between the API, service, and database layers
- [Architecture Overview](../architecture/overview.md) — System component structure and data access layer description
- [Configuration Guide](../getting-started/configuration.md) — Database environment variable configuration
