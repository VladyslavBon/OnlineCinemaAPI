import os

from database.validators import accounts as account_validators
from database.session_sqlite import reset_sqlite_database as reset_database


environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db
    )
else:
    from database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )

