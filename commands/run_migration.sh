#!/bin/sh

# SQLAlchemy migrate
ALEMBIC_CONFIG="/usr/src/alembic.ini"
MIGRATIONS_DIR="/usr/src/fastapi/database/migrations/versions"

echo "Checking for changes before generating a migration..."

# Ensure the migrations folder exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Migrations folder does not exist. Creating it..."
    mkdir -p "$MIGRATIONS_DIR"
fi

# Check if the alembic_version table exists in the database
export PGPASSWORD="$POSTGRES_PASSWORD"

if ! psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt" | grep -q "alembic_version"; then
    echo "Alembic version table not found. Applying all migrations..."

    # Check if there are existing migration files
    if [ -z "$(ls -A "$MIGRATIONS_DIR")" ]; then
        echo "No migration files found. Generating initial migration..."
        alembic -c $ALEMBIC_CONFIG revision --autogenerate -m "initial migration"
    fi

    echo "Applying all migrations..."
    alembic -c $ALEMBIC_CONFIG upgrade head

    # Run database saver script only if alembic_version table was just created
    echo "Running database saver script..."
    python -m load_fixture
    echo "Database saver script completed."

    exit 0
fi

# Generate temporary migration
if ! alembic -c $ALEMBIC_CONFIG revision --autogenerate -m "temp_migration"; then
    echo "Error generating migration. Exiting."
    exit 1
fi

# Find the last created migration file
LAST_MIGRATION=$(find "$MIGRATIONS_DIR" -type f -printf '%T+ %p\n' | sort | tail -n 1 | awk '{print $2}')

# Show migration content
echo "Generated migration content:"
cat "$LAST_MIGRATION"

# Check if the migration contains real changes
if grep -qE '^\s*pass\s*$' "$LAST_MIGRATION"; then
    echo "No changes detected. Deleting temporary migration."
    rm "$LAST_MIGRATION"
else
    echo "Changes detected. Applying migration."
    alembic -c $ALEMBIC_CONFIG upgrade head
fi

# Run database saver script
echo "Running database saver script..."
python -m load_fixture
echo "Database saver script completed."
