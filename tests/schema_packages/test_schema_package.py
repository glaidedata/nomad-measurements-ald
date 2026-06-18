from unittest.mock import MagicMock, patch

import pandas as pd
from nomad.datamodel.datamodel import EntryArchive, EntryMetadata

from nomad_measurements_ald.schema_packages.schema_package import ELNItalyaALD


@patch("nomad_measurements_ald.schema_packages.schema_package.read_italya_ald")
def test_eln_italya_ald_normalize(mock_read_italya_ald):
    """Test that the normalizer maps parsed ALD data and calculates telemetry correctly."""

    # 1. Construct a mock return object for the external reader
    mock_ald_data = MagicMock()
    mock_ald_data.system_name = "Italya ALD Test"
    mock_ald_data.start_timestamp = "10.02.2026 15:33:22"
    mock_ald_data.metadata = {"version": "1.0"}
    mock_ald_data.port_configurations = {"port1": "H2O"}
    mock_ald_data.precursor_doses = {"H2O": 0.5}
    mock_ald_data.running_rcp = [["1"], ["2", "Heater", "1", "90", "C"]]

    # Create a mock pandas DataFrame for sensor telemetry
    df = pd.DataFrame({
        "timestamp": ["10.02.2026 15:33:22", "10.02.2026 15:33:23"],
        "sensor": ["Heater1", "Heater1"],
        "value": [90.0, 90.5]
    })
    mock_ald_data.communication_data = df

    # Assign the mock object to the patched reader function
    mock_read_italya_ald.return_value = mock_ald_data

    # 2. Setup NOMAD Archive and mock the file system context
    archive = EntryArchive()
    archive.metadata = EntryMetadata(entry_name="test_entry.txt")
    archive.m_context = MagicMock()
    mock_raw_file = MagicMock()
    mock_raw_file.os_path = "/fake/path/to/test.txt"
    archive.m_context.upload_files.raw_file_object.return_value = mock_raw_file

    # 3. Instantiate the schema and run normalize
    entry = ELNItalyaALD()
    entry.data_file = "test.txt"
    entry.normalize(archive, None)

    # 4. Assert Top-Level Metadata
    assert entry.system_name == "Italya ALD Test"
    assert entry.start_timestamp == "10.02.2026 15:33:22"
    assert entry.raw_metadata == {"version": "1.0"}

    # 5. Assert Measurement Data (JSON dictionaries)
    meas_data = entry.results[0].data
    assert meas_data.port_configurations == {"port1": "H2O"}
    assert meas_data.precursor_doses == {"H2O": 0.5}
    assert meas_data.running_recipe == {"steps": [["1"], ["2", "Heater", "1", "90", "C"]]}

    # 6. Assert Sensor Logs & Time Math
    sensor_logs = meas_data.sensor_logs
    assert len(sensor_logs) == 1
    assert sensor_logs[0].sensor_name == "Heater1"

    # Check that time relative seconds calculated correctly (0.0s and 1.0s)
    assert list(sensor_logs[0].time.magnitude) == [0.0, 1.0]
    assert list(sensor_logs[0].value) == [90.0, 90.5]