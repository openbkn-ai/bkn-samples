from load_sample_data import infer_column_type


def test_infer_int():
    assert infer_column_type(["1", "2", "3"]) in ("INTEGER", "BIGINT")


def test_infer_float():
    assert infer_column_type(["1.5", "2.0", ""]) == "FLOAT"


def test_infer_date():
    assert infer_column_type(["2026-01-01", "2026-02-03"]) in ("DATE", "TIMESTAMP", "TEXT")


def test_infer_text_fallback():
    assert infer_column_type(["A", "B1", "中文"]) == "TEXT"


def test_mysql_type_map():
    from load_sample_data import sql_type_for

    assert "BIGINT" in sql_type_for("BIGINT", "mysql").upper() or "INT" in sql_type_for("BIGINT", "mysql").upper()
    assert sql_type_for("TEXT", "mysql") in ("TEXT", "LONGTEXT")


def test_quote_ident_by_engine():
    from load_sample_data import quote_ident

    assert quote_ident("my_table", "postgres") == '"my_table"'
    assert quote_ident("my_table", "sqlite") == '"my_table"'
    assert quote_ident("my_table", "mysql") == "`my_table`"


def test_sql_type_for_all_engines():
    from load_sample_data import sql_type_for

    assert sql_type_for("BIGINT", "postgres") == "BIGINT"
    assert sql_type_for("BIGINT", "sqlite") == "INTEGER"
    assert sql_type_for("FLOAT", "postgres") == "DOUBLE PRECISION"
    assert sql_type_for("TIMESTAMP", "mysql") == "DATETIME"


def test_explicit_schema_keeps_numeric_looking_identifiers_as_varchar():
    from load_sample_data import column_schema

    assert column_schema("customer_entity", "contact_phone", ["13800138000"], "mysql") == (
        "contact_phone", "VARCHAR(32)"
    )
    assert column_schema("erp_material", "material_code", ["10001"], "mysql") == (
        "material_code", "VARCHAR(64)"
    )


def test_explicit_schema_uses_decimal_for_prices_and_quantities():
    from load_sample_data import column_schema

    assert column_schema("erp_material", "material_standard_price", ["0"], "mysql") == (
        "material_standard_price", "DECIMAL(18,6)"
    )
    assert column_schema("erp_purchase_order", "qty", ["0"], "mysql") == (
        "qty", "DECIMAL(18,6)"
    )
