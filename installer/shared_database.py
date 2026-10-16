"""One product-provisioned MariaDB runtime, with per-installation database ownership."""

import json
import os
import re
import secrets
import uuid
from contextlib import contextmanager
from pathlib import Path

from installer.deploy_database import DeployError, _sample
from installer.hook_process import run_hook
from installer.state_store import write_json
from installer.studio_api import _read_state

KIND = "shared-mariadb"
IDENTIFIER = re.compile(r"[a-z0-9_]{1,64}")


def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise DeployError("ownership_conflict", "Invalid sample database identity.")
    return "`" + value + "`"


def configured():
    return bool(os.environ.get("BKN_SAMPLE_DB_HOST"))


def settings():
    return {"host": os.environ["BKN_SAMPLE_DB_HOST"],
            "port": int(os.environ.get("BKN_SAMPLE_DB_PORT", "3306")),
            "user": os.environ.get("BKN_SAMPLE_DB_ADMIN_USER", "root"),
            "password": Path(os.environ["BKN_SAMPLE_DB_PASSWORD_FILE"]).read_text(),
            "database": os.environ["BKN_SAMPLE_DB_REGISTRY"]}


@contextmanager
def manager(database):
    import pymysql
    config = settings()
    # Never continue against a different runtime after an operator changes configuration.
    if database["host"] != config["host"] or database["port"] != config["port"]:
        raise DeployError("ownership_conflict", "The sample database runtime differs from its installation receipt.")
    connection = pymysql.connect(**config, connect_timeout=10, read_timeout=30,
                                 write_timeout=30, autocommit=True)
    lock = "bkn-sample-database-ownership"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION lock_wait_timeout=10")
            cursor.execute("SELECT GET_LOCK(%s, 10)", (lock,))
            if cursor.fetchone()[0] != 1:
                raise DeployError("database_busy", "Sample database is busy; retry the operation.")
            cursor.execute("CREATE TABLE IF NOT EXISTS sample_ownership (database_name VARCHAR(64) PRIMARY KEY, sample_id VARCHAR(32) NOT NULL, version VARCHAR(32) NOT NULL, ownership CHAR(32) NOT NULL, database_user VARCHAR(32) NOT NULL, deleted BOOLEAN NOT NULL DEFAULT FALSE)")
            yield cursor
    finally:
        connection.close()  # Also releases the advisory lock on failure.


def _schemas(cursor, names):
    cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN (%s, %s)", names)
    return {row[0] for row in cursor.fetchall()}


def _owner(cursor, database):
    cursor.execute("SELECT sample_id, version, ownership, database_user, deleted FROM sample_ownership WHERE database_name=%s", (database["name"],))
    return cursor.fetchone()


def _matches(owner, database, sample, version):
    return owner and tuple(owner[:4]) == (sample, version, database["ownership"], database["user"])


def prepare(root, sample, version, state_dir, run):
    directory, document = _sample(root, sample)
    if document["spec"]["data"]["mode"] != "embedded":
        raise DeployError("invalid_package", "The shared sample runtime requires package-local data.")
    name = document["spec"]["database"]["name"]
    staging = name + "_loading"
    identifier(name)
    identifier(staging)
    config = settings()
    if config["database"] in (name, staging) or name in {"mysql", "sys", "information_schema", "performance_schema"}:
        raise DeployError("ownership_conflict", "Sample database conflicts with the runtime registry.")
    record = _read_state(state_dir, sample)
    if not record or record["version"] != version:
        raise DeployError("ownership_conflict", "The accepted installation receipt is missing.")
    database = record.get("databaseRuntime")
    credentials = state_dir / sample / "database-credentials.json"
    if database is None:
        # An old, partially installed per-sample runtime must first be uninstalled.
        if bool(record.get("stages")) or record.get("catalogId"):
            raise DeployError("runtime_upgrade_required", "Uninstall the original sample before installing on the shared runtime.")
        database = {"kind": KIND, "name": name, "staging": staging,
                    "host": config["host"], "port": config["port"],
                    "user": "bkn_" + uuid.uuid4().hex[:24], "ownership": uuid.uuid4().hex}
        # Persist credentials before the resource receipt, and both before any DB mutation.
        write_json(credentials, {"password": secrets.token_urlsafe(32), "ownership": database["ownership"]})
        record["databaseRuntime"] = database
        record.setdefault("stages", {})["database"] = "running"
        write_json(state_dir / f"{sample}.json", record)
    if database.get("kind") != KIND or database["name"] != name or database["staging"] != staging:
        raise DeployError("ownership_conflict", "Database identity differs from the accepted sample.")
    secret = json.loads(credentials.read_text())
    if secret.get("ownership") != database["ownership"]:
        raise DeployError("ownership_conflict", "Database credentials differ from the installation receipt.")
    password = secret["password"]
    with manager(database) as cursor:
        cursor.execute("SELECT database_name FROM sample_ownership WHERE deleted=FALSE AND (database_name=%s OR CONCAT(database_name, '_loading')=%s)", (staging, name))
        if cursor.fetchone():
            raise DeployError("ownership_conflict", "A staging database is reserved by another sample.")
        owner = _owner(cursor, database)
        existing = _schemas(cursor, (name, staging))
        if not _matches(owner, database, sample, version):
            if existing or (owner and not owner[4]):
                raise DeployError("ownership_conflict", "A database already belongs to another installation.")
            cursor.execute("REPLACE INTO sample_ownership VALUES (%s,%s,%s,%s,%s,FALSE)",
                           (name, sample, version, database["ownership"], database["user"]))
        elif owner[4]:
            raise DeployError("ownership_conflict", "The installation database has already been removed.")
        cursor.execute("CREATE DATABASE IF NOT EXISTS " + identifier(name) + " CHARACTER SET utf8mb4")
        cursor.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (database["user"], password))
        # GRANT database names treat '_' as a pattern; escape it for exact ownership.
        for schema in (name, staging):
            grant = "`" + schema.replace("_", "\\_") + "`"
            cursor.execute("GRANT ALL PRIVILEGES ON " + grant + ".* TO %s@'%%'", (database["user"],))
    environment = {"MYSQL_HOST": database["host"], "MYSQL_PORT": str(database["port"]),
                   "MYSQL_DATABASE": name, "MYSQL_ADMIN_DATABASE": name,
                   "MYSQL_USER": database["user"], "MYSQL_PASSWORD": password,
                   "BKN_SAMPLE_ID": sample, "BKN_SAMPLE_VERSION": version,
                   "BKN_SAMPLE_CACHE": str(state_dir / sample / "cache")}
    for hook in ("dbInit", "dbVerify"):
        result = run_hook(directory, directory / document["spec"]["hooks"][hook], run, environment)
        if result.returncode:
            # Hook output may contain credentials; retain a safe stage-level message.
            raise DeployError("database_not_ready", "Sample database loading or verification failed; retry the installation.")
    return {"name": name, "host": database["host"], "port": database["port"],
            "user": database["user"], "password": password}


def validate_owner(record):
    database = record["databaseRuntime"]
    if database.get("kind") != KIND:
        raise DeployError("ownership_conflict", "Unknown database ownership receipt.")
    for name in (database["name"], database["staging"]):
        identifier(name)
    if database["staging"] != database["name"] + "_loading":
        raise DeployError("ownership_conflict", "Invalid staging database ownership.")
    with manager(database) as cursor:
        owner = _owner(cursor, database)
        # Receipt persistence precedes DB mutation. A connection failure before
        # claiming ownership leaves no resources, which is safe to clean up.
        if owner is None and not _schemas(cursor, (database["name"], database["staging"])):
            return
        if not _matches(owner, database, record["sample"], record["version"]):
            raise DeployError("ownership_conflict", "Sample database ownership differs; nothing will be deleted.")


def remove(record):
    database = record["databaseRuntime"]
    validate_owner(record)
    with manager(database) as cursor:
        owner = _owner(cursor, database)
        if owner is None and not _schemas(cursor, (database["name"], database["staging"])):
            return
        if not _matches(owner, database, record["sample"], record["version"]):
            raise DeployError("ownership_conflict", "Sample database ownership differs.")
        for name in (database["staging"], database["name"]):
            cursor.execute("DROP DATABASE IF EXISTS " + identifier(name))
        cursor.execute("DROP USER IF EXISTS %s@'%%'", (database["user"],))
        if _schemas(cursor, (database["name"], database["staging"])):
            raise DeployError("database_busy", "Sample database deletion is pending; retry uninstall.")
        cursor.execute("UPDATE sample_ownership SET deleted=TRUE WHERE database_name=%s AND ownership=%s", (database["name"], database["ownership"]))
