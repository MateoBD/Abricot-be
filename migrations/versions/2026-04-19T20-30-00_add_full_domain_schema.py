"""add full domain schema tables

Revision ID: f7d329a1b4ce
Revises: c8f4a2b91d3e
Create Date: 2026-04-19 20:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "f7d329a1b4ce"
down_revision = "c8f4a2b91d3e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("iso_code", sa.String(length=3), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso_code"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "provinces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country_id", "name", name="uq_province_country_name"),
    )
    op.create_index(op.f("ix_provinces_country_id"), "provinces", ["country_id"], unique=False)

    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("province_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["province_id"], ["provinces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("province_id", "name", name="uq_city_province_name"),
    )
    op.create_index(op.f("ix_cities_province_id"), "cities", ["province_id"], unique=False)

    op.create_table(
        "neighbourhoods",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "name", name="uq_neighbourhood_city_name"),
    )
    op.create_index(
        op.f("ix_neighbourhoods_city_id"),
        "neighbourhoods",
        ["city_id"],
        unique=False,
    )

    op.create_table(
        "price_ranges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=10), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "cuisine_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.add_column("restaurants", sa.Column("city_id", sa.Integer(), nullable=True))
    op.add_column("restaurants", sa.Column("neighbourhood_id", sa.Integer(), nullable=True))
    op.add_column("restaurants", sa.Column("price_range_id", sa.Integer(), nullable=True))
    op.add_column(
        "restaurants",
        sa.Column("allow_table_joining", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "restaurants",
        sa.Column(
            "default_slot_duration_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("90"),
        ),
    )
    op.create_index(op.f("ix_restaurants_city_id"), "restaurants", ["city_id"], unique=False)
    op.create_index(
        op.f("ix_restaurants_neighbourhood_id"),
        "restaurants",
        ["neighbourhood_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_restaurants_price_range_id"),
        "restaurants",
        ["price_range_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_restaurants_city_id",
        "restaurants",
        "cities",
        ["city_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_restaurants_neighbourhood_id",
        "restaurants",
        "neighbourhoods",
        ["neighbourhood_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_restaurants_price_range_id",
        "restaurants",
        "price_ranges",
        ["price_range_id"],
        ["id"],
    )

    op.create_table(
        "restaurant_admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "restaurant_id",
            name="uq_restaurant_admin_user_restaurant",
        ),
    )
    op.create_index(
        op.f("ix_restaurant_admins_user_id"),
        "restaurant_admins",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_restaurant_admins_restaurant_id"),
        "restaurant_admins",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "restaurant_cuisines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("cuisine_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["cuisine_type_id"], ["cuisine_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id",
            "cuisine_type_id",
            name="uq_restaurant_cuisine_restaurant_type",
        ),
    )
    op.create_index(
        op.f("ix_restaurant_cuisines_restaurant_id"),
        "restaurant_cuisines",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_restaurant_cuisines_cuisine_type_id"),
        "restaurant_cuisines",
        ["cuisine_type_id"],
        unique=False,
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("receive_promotions", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("receive_order_updates", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "receive_reservation_reminders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "restaurant_id",
            name="uq_notification_pref_user_restaurant",
        ),
    )
    op.create_index(
        op.f("ix_notification_preferences_user_id"),
        "notification_preferences",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_preferences_restaurant_id"),
        "notification_preferences",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("is_joinable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "number", name="uq_table_restaurant_number"),
    )
    op.create_index(op.f("ix_tables_restaurant_id"), "tables", ["restaurant_id"], unique=False)

    op.create_table(
        "business_hours",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=True),
        sa.Column("closes_at", sa.Time(), nullable=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id",
            "day_of_week",
            name="uq_business_hours_restaurant_day",
        ),
    )
    op.create_index(
        op.f("ix_business_hours_restaurant_id"),
        "business_hours",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("guest_name", sa.String(length=150), nullable=True),
        sa.Column("guest_phone", sa.String(length=30), nullable=True),
        sa.Column("guest_email", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time_slot", sa.Time(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="CONFIRMED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmation_code", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("confirmation_code"),
    )
    op.create_index(
        op.f("ix_reservations_restaurant_id"),
        "reservations",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(op.f("ix_reservations_user_id"), "reservations", ["user_id"], unique=False)
    op.create_index(op.f("ix_reservations_date"), "reservations", ["date"], unique=False)
    op.create_index(op.f("ix_reservations_status"), "reservations", ["status"], unique=False)

    op.create_table(
        "reservation_tables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", "table_id", name="uq_reservation_table_pair"),
    )
    op.create_index(
        op.f("ix_reservation_tables_reservation_id"),
        "reservation_tables",
        ["reservation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reservation_tables_table_id"),
        "reservation_tables",
        ["table_id"],
        unique=False,
    )

    op.create_table(
        "menus",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_menus_restaurant_id"), "menus", ["restaurant_id"], unique=False)

    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("menu_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["menu_id"], ["menus.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_menu_categories_menu_id"),
        "menu_categories",
        ["menu_id"],
        unique=False,
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["category_id"], ["menu_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_menu_items_category_id"), "menu_items", ["category_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("estimated_ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_restaurant_id"), "orders", ["restaurant_id"], unique=False)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_menu_item_id"), "order_items", ["menu_item_id"], unique=False)

    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", sa.String(length=32), nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_users", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_promotions_restaurant_id"),
        "promotions",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "promotion_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("promotion_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.ForeignKeyConstraint(["promotion_id"], ["promotions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("promotion_id", "menu_item_id", name="uq_promotion_item_pair"),
    )
    op.create_index(
        op.f("ix_promotion_items_promotion_id"),
        "promotion_items",
        ["promotion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promotion_items_menu_item_id"),
        "promotion_items",
        ["menu_item_id"],
        unique=False,
    )

    price_ranges_table = sa.table(
        "price_ranges",
        sa.column("slug", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        price_ranges_table,
        [
            {
                "slug": "ECONOMICO",
                "label": "$",
                "description": "Menos de $5.000 por persona",
                "sort_order": 1,
            },
            {
                "slug": "MODERADO",
                "label": "$$",
                "description": "$5.000 - $15.000 por persona",
                "sort_order": 2,
            },
            {
                "slug": "ELEGANTE",
                "label": "$$$",
                "description": "$15.000 - $40.000 por persona",
                "sort_order": 3,
            },
            {
                "slug": "EXCLUSIVO",
                "label": "$$$$",
                "description": "Mas de $40.000 por persona",
                "sort_order": 4,
            },
        ],
    )

    cuisine_types_table = sa.table(
        "cuisine_types",
        sa.column("slug", sa.String),
        sa.column("label", sa.String),
    )
    op.bulk_insert(
        cuisine_types_table,
        [
            {"slug": "ARGENTINA", "label": "Parrilla y Criolla"},
            {"slug": "ITALIANA", "label": "Pasta y Pizza"},
            {"slug": "JAPONESA", "label": "Sushi y Ramen"},
            {"slug": "MEDITERRANEA", "label": "Mediterranea"},
            {"slug": "MEXICANA", "label": "Mexicana"},
            {"slug": "PERUANA", "label": "Peruana"},
            {"slug": "AMERICANA", "label": "Americana"},
            {"slug": "CHINA", "label": "China"},
            {"slug": "FRANCESA", "label": "Francesa"},
            {"slug": "CAFE_BAR", "label": "Cafe y Bar"},
            {"slug": "VEGANA_VEGETARIANA", "label": "Vegana y Vegetariana"},
            {"slug": "MARISCOS", "label": "Mariscos"},
            {"slug": "FUSION", "label": "Fusion"},
            {"slug": "OTRA", "label": "Otra"},
        ],
    )


def downgrade():
    op.drop_index(op.f("ix_promotion_items_menu_item_id"), table_name="promotion_items")
    op.drop_index(op.f("ix_promotion_items_promotion_id"), table_name="promotion_items")
    op.drop_table("promotion_items")

    op.drop_index(op.f("ix_promotions_restaurant_id"), table_name="promotions")
    op.drop_table("promotions")

    op.drop_index(op.f("ix_order_items_menu_item_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_restaurant_id"), table_name="orders")
    op.drop_table("orders")

    op.drop_index(op.f("ix_menu_items_category_id"), table_name="menu_items")
    op.drop_table("menu_items")

    op.drop_index(op.f("ix_menu_categories_menu_id"), table_name="menu_categories")
    op.drop_table("menu_categories")

    op.drop_index(op.f("ix_menus_restaurant_id"), table_name="menus")
    op.drop_table("menus")

    op.drop_index(op.f("ix_reservation_tables_table_id"), table_name="reservation_tables")
    op.drop_index(op.f("ix_reservation_tables_reservation_id"), table_name="reservation_tables")
    op.drop_table("reservation_tables")

    op.drop_index(op.f("ix_reservations_status"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_date"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_user_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_restaurant_id"), table_name="reservations")
    op.drop_table("reservations")

    op.drop_index(op.f("ix_business_hours_restaurant_id"), table_name="business_hours")
    op.drop_table("business_hours")

    op.drop_index(op.f("ix_tables_restaurant_id"), table_name="tables")
    op.drop_table("tables")

    op.drop_index(
        op.f("ix_notification_preferences_restaurant_id"),
        table_name="notification_preferences",
    )
    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_table("notification_preferences")

    op.drop_index(op.f("ix_restaurant_cuisines_cuisine_type_id"), table_name="restaurant_cuisines")
    op.drop_index(op.f("ix_restaurant_cuisines_restaurant_id"), table_name="restaurant_cuisines")
    op.drop_table("restaurant_cuisines")

    op.drop_index(op.f("ix_restaurant_admins_restaurant_id"), table_name="restaurant_admins")
    op.drop_index(op.f("ix_restaurant_admins_user_id"), table_name="restaurant_admins")
    op.drop_table("restaurant_admins")

    op.drop_constraint("fk_restaurants_price_range_id", "restaurants", type_="foreignkey")
    op.drop_constraint("fk_restaurants_neighbourhood_id", "restaurants", type_="foreignkey")
    op.drop_constraint("fk_restaurants_city_id", "restaurants", type_="foreignkey")
    op.drop_index(op.f("ix_restaurants_price_range_id"), table_name="restaurants")
    op.drop_index(op.f("ix_restaurants_neighbourhood_id"), table_name="restaurants")
    op.drop_index(op.f("ix_restaurants_city_id"), table_name="restaurants")
    op.drop_column("restaurants", "default_slot_duration_minutes")
    op.drop_column("restaurants", "allow_table_joining")
    op.drop_column("restaurants", "price_range_id")
    op.drop_column("restaurants", "neighbourhood_id")
    op.drop_column("restaurants", "city_id")

    op.drop_table("cuisine_types")
    op.drop_table("price_ranges")

    op.drop_index(op.f("ix_neighbourhoods_city_id"), table_name="neighbourhoods")
    op.drop_table("neighbourhoods")

    op.drop_index(op.f("ix_cities_province_id"), table_name="cities")
    op.drop_table("cities")

    op.drop_index(op.f("ix_provinces_country_id"), table_name="provinces")
    op.drop_table("provinces")

    op.drop_table("countries")
