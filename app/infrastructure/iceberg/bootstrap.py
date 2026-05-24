from __future__ import annotations

from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import DayTransform
from pyiceberg.types import DoubleType, LongType, NestedField, StringType, TimestampType

from app.core.config import Settings
from app.infrastructure.iceberg.catalog import (
    load_iceberg_catalog,
    resolve_iceberg_identifier,
    resolve_iceberg_namespace,
)


def build_telemetry_schema() -> Schema:
    fields = [
        NestedField(1, "stored_filename", StringType()),
        NestedField(2, "fetched_at", TimestampType()),
        NestedField(3, "device_imei", LongType()),
        NestedField(4, "vehicle_registration", StringType()),
        NestedField(5, "vehicle_name", StringType()),
        NestedField(6, "company_name", StringType()),
        NestedField(7, "branch_name", StringType()),
        NestedField(8, "vehicle_type", StringType()),
        NestedField(9, "device_model", StringType()),
        NestedField(10, "vehicle_status", StringType()),
        NestedField(11, "power_state", StringType()),
        NestedField(12, "ignition_state", StringType()),
        NestedField(13, "gps_state", StringType()),
        NestedField(14, "speed_kph", LongType()),
        NestedField(15, "heading_angle", LongType()),
        NestedField(16, "course", LongType()),
        NestedField(17, "odometer", LongType()),
        NestedField(18, "can_odometer", LongType()),
        NestedField(19, "latitude", DoubleType()),
        NestedField(20, "longitude", DoubleType()),
        NestedField(21, "location_text", StringType()),
        NestedField(22, "point_of_interest", StringType()),
        NestedField(23, "gps_actual_time", TimestampType()),
        NestedField(24, "recorded_at", TimestampType()),
        NestedField(25, "temperature", LongType()),
        NestedField(26, "external_voltage", DoubleType()),
        NestedField(27, "battery_percentage", LongType()),
        NestedField(28, "satellite_count", LongType()),
        NestedField(29, "gps_hdop", DoubleType()),
        NestedField(30, "fuel_level", LongType()),
        NestedField(31, "ac_state", StringType()),
        NestedField(32, "sos_state", StringType()),
        NestedField(33, "immobilize_state", StringType()),
        NestedField(34, "door_1_state", StringType()),
        NestedField(35, "door_2_state", StringType()),
        NestedField(36, "door_3_state", StringType()),
        NestedField(37, "door_4_state", StringType()),
        NestedField(38, "electronic_lock_state", StringType()),
        NestedField(39, "driver_first_name", StringType()),
        NestedField(40, "driver_middle_name", StringType()),
        NestedField(41, "driver_last_name", StringType()),
        NestedField(42, "driver_ibutton_rfid", StringType()),
        NestedField(43, "vin", StringType()),
        NestedField(44, "mobile_country_code", LongType()),
        NestedField(45, "mobile_network_code", LongType()),
        NestedField(46, "cell_id", LongType()),
        NestedField(47, "location_area_code", LongType()),
        NestedField(48, "heartbeat", LongType()),
        NestedField(49, "source_username", StringType()),
        NestedField(50, "altitude", LongType()),
    ]
    return Schema(*fields)


def build_telemetry_partition_spec(schema: Schema) -> PartitionSpec:
    recorded_at_field = schema.find_field("recorded_at")
    return PartitionSpec(
        PartitionField(
            source_id=recorded_at_field.field_id,
            field_id=1000,
            transform=DayTransform(),
            name="recorded_at_day",
        )
    )


def bootstrap_iceberg_table(settings: Settings) -> None:
    catalog = load_iceberg_catalog(settings)
    namespace = resolve_iceberg_namespace(settings)
    table_identifier = resolve_iceberg_identifier(settings)
    schema = build_telemetry_schema()
    partition_spec = build_telemetry_partition_spec(schema)

    if not catalog.namespace_exists(namespace):
        catalog.create_namespace_if_not_exists(namespace)

    if not catalog.table_exists(table_identifier):
        catalog.create_table(
            table_identifier,
            schema=schema,
            partition_spec=partition_spec,
        )
