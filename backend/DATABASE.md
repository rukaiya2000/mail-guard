# Database Guide

## Schema Overview

### Users Table
```sql
id (Primary Key)
username (Unique, Indexed)
email (Unique, Indexed)
hashed_password
google_id (Unique, Nullable)
google_access_token (Nullable)
role (Default: "user", Indexed)
created_at (DateTime, Indexed)
```

**Relationships:**
- One-to-Many: classifications (CASCADE delete)
- One-to-Many: activity_logs (CASCADE delete)

### Classification Logs Table
```sql
id (Primary Key)
user_id (Foreign Key → users.id, Indexed, Nullable)
timestamp (DateTime, Indexed)
email_hash (String(64), Indexed, Nullable)
email_snippet (String(200))
label (String(20), Indexed)
confidence (Float)
reasoning (String)
latency_ms (Float)
tokens_used (Integer)
success (Boolean, Indexed)
error_message (Nullable)
gmail_message_id (Indexed, Nullable)
```

**Composite Indexes:**
- `ix_user_timestamp` (user_id, timestamp)
- `ix_user_label` (user_id, label)
- `ix_user_success` (user_id, success)
- `ix_label_timestamp` (label, timestamp)
- `ix_email_hash_user` (email_hash, user_id)

### Activity Logs Table
```sql
id (Primary Key)
user_id (Foreign Key → users.id, Indexed, Nullable)
action (String(50), Indexed)
details (String, Nullable)
ip_address (String(45), Nullable)
timestamp (DateTime, Indexed)
status (String(20), Default: "success")
```

**Composite Indexes:**
- `ix_user_action` (user_id, action)
- `ix_user_timestamp_activity` (user_id, timestamp)
- `ix_action_status` (action, status)

## Query Optimization

### Common Queries and Their Indexes

#### Get user's recent classifications
```python
query = db.query(ClassificationLog)\
    .filter(ClassificationLog.user_id == user_id)\
    .filter(ClassificationLog.success == True)\
    .order_by(ClassificationLog.timestamp.desc())\
    .limit(50)
```
**Uses:** `ix_user_timestamp` or `ix_user_success`

#### Get classifications by label
```python
query = db.query(ClassificationLog)\
    .filter(ClassificationLog.label == "PHISHING")\
    .filter(ClassificationLog.success == True)\
    .order_by(ClassificationLog.timestamp.desc())
```
**Uses:** `ix_label_timestamp`

#### Get user activity
```python
query = db.query(ActivityLog)\
    .filter(ActivityLog.user_id == user_id)\
    .order_by(ActivityLog.timestamp.desc())
```
**Uses:** `ix_user_timestamp_activity`

#### Check for duplicate email (cache)
```python
cached = db.query(ClassificationLog)\
    .filter(ClassificationLog.email_hash == email_hash)\
    .filter(ClassificationLog.user_id == user_id)\
    .filter(ClassificationLog.timestamp >= cutoff_time)\
    .first()
```
**Uses:** `ix_email_hash_user`

## Performance Considerations

### Pagination
Always paginate large result sets:
```python
logs = query.offset(offset).limit(limit).all()
```

### Lazy Loading
Use eager loading for relationships when needed:
```python
from sqlalchemy.orm import joinedload
logs = db.query(ClassificationLog)\
    .options(joinedload(ClassificationLog.user))\
    .filter(...)\
    .all()
```

### Connection Pooling
PostgreSQL connections are pooled (set in config):
```python
create_engine(DATABASE_URL, pool_pre_ping=True)
```

### Batch Operations
For bulk inserts, use bulk_insert_mappings:
```python
db.bulk_insert_mappings(ClassificationLog, records)
db.commit()
```

## Migration Guide

### Updating from Old Schema

If upgrading from a previous version:

1. **Backup your database:**
   ```bash
   cp sentinel.db sentinel.db.backup
   ```

2. **Delete old database (development only):**
   ```bash
   rm sentinel.db
   ```

3. **Restart the application:**
   The new schema will be created automatically on startup.

### For Production (PostgreSQL)

Use Alembic for migrations:

```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "Add indexes and foreign keys"
alembic upgrade head
```

## Maintenance

### Analyzing Query Performance

#### SQLite
```sql
EXPLAIN QUERY PLAN
SELECT * FROM classification_logs
WHERE user_id = 1
ORDER BY timestamp DESC;
```

#### PostgreSQL
```sql
EXPLAIN ANALYZE
SELECT * FROM classification_logs
WHERE user_id = 1
ORDER BY timestamp DESC;
```

### Reindexing

#### SQLite
```sql
REINDEX;
```

#### PostgreSQL
```sql
REINDEX DATABASE sentinel;
```

### Vacuuming (cleanup)

#### SQLite
```sql
VACUUM;
```

#### PostgreSQL
```sql
VACUUM ANALYZE;
```

## Backup & Recovery

### SQLite Backup
```bash
sqlite3 sentinel.db ".backup sentinel_backup.db"
```

### PostgreSQL Backup
```bash
pg_dump -h localhost -U user -d sentinel > sentinel_backup.sql
```

### PostgreSQL Restore
```bash
psql -h localhost -U user -d sentinel < sentinel_backup.sql
```

## Monitoring

### Check Database Size

#### SQLite
```bash
ls -lh sentinel.db
```

#### PostgreSQL
```sql
SELECT pg_size_pretty(pg_database_size('sentinel'));
```

### Index Usage

#### PostgreSQL
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as number_of_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Slow Queries

Enable slow query logging for PostgreSQL:
```sql
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1 second
SELECT pg_reload_conf();
```

## Best Practices

1. **Always use indexes for WHERE clauses**
2. **Composite indexes for multi-column filters**
3. **Paginate large result sets**
4. **Use relationships for data integrity (FK constraints)**
5. **Cascade delete for cleanup**
6. **Analyze query plans regularly**
7. **Backup database regularly**
8. **Monitor slow queries**
