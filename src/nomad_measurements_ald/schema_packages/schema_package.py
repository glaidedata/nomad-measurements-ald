from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ientrance_instruments.schema_packages.schema_package import IEntranceInstrument
from nomad.datamodel.data import JSON, ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import ELNComponentEnum
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection

# Import the reader from readers package
from readers_ientrance.ald_reader import read_italya_ald

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = SchemaPackage()


# ==========================================
# 1. SHARED ALD SETUP SECTIONS
# ==========================================
class SensorLog(ArchiveSection):
    """A section to hold time-series data for a single sensor."""

    m_def = Section(
        a_plot=[
            dict(
                label='Sensor Value over Time',
                x='time',
                y='value',
                lines=[dict(mode='lines', line=dict(color='blue'))],
            )
        ]
    )

    sensor_name = Quantity(
        type=str,
        description='Name of the sensor (e.g., Pressure, Heater1, RotationMotor).',
    )

    time = Quantity(
        type=np.float64,
        shape=['*'],
        unit='s',
        description='Relative time in seconds from the start of the measurement.',
    )

    value = Quantity(
        type=np.float64,
        shape=['*'],
        description='The recorded value of the sensor.',
    )


# ==========================================
# 2. SHARED ALD RESULTS
# ==========================================
class ALDMeasurementData(ArchiveSection):
    """A section to hold the processed ALD logs and sensor telemetry."""

    port_configurations = Quantity(
        type=JSON,
        description='Mapping of system ports to their respective chemicals/gases.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    precursor_doses = Quantity(
        type=JSON,
        description='Cumulative dose times for each precursor.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    running_recipe = Quantity(
        type=JSON,
        description='The sequential recipe steps executed during the process.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    sensor_logs = SubSection(section_def=SensorLog, repeats=True)


class ALDResult(MeasurementResult):
    data = SubSection(section_def=ALDMeasurementData)


# ==========================================
# 3. BASE ALD ENTRY
# ==========================================
class BaseALDSpectroscopy(Measurement):
    """Base class containing shared attributes for all ALD entries."""

    # We define a hidden field using the custom instrument type.
    # Its ONLY purpose is to preload the IEntranceInstrument schema
    _instrument_schema_preload = Quantity(type=IEntranceInstrument)

    data_file = Quantity(
        type=str,
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor'),
        description='The raw ALD log text file.',
    )

    system_name = Quantity(
        type=str,
        description='The configured name of the ALD system.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    start_timestamp = Quantity(
        type=str,
        description='The starting timestamp of the ALD process.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    raw_metadata = Quantity(
        type=JSON,
        description='A complete dictionary dump of unparsed System Configurations.',
    )

    results = SubSection(section_def=ALDResult, repeats=True)


# ==========================================
# 4. ITALYA ALD SPECIFIC SCHEMA
# ==========================================
class ELNItalyaALD(BaseALDSpectroscopy, EntryData):
    m_def = Section(
        label='Italya ALD Measurement',
        a_eln=dict(lane_width='600px'),
        a_template=dict(measurement_identifiers=dict()),
    )

    def _init_subsections(self):
        """Helper method to initialize empty schema sections."""
        if not self.results:
            self.results = [ALDResult()]
        if not self.results[0].data:
            self.results[0].data = ALDMeasurementData()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        if not self.data_file:
            super().normalize(archive, logger)
            return

        try:
            # 1. Get the absolute OS path directly
            file_path = archive.m_context.upload_files.raw_file_object(
                self.data_file
            ).os_path

            # 2. Parse the data using the custom reader
            ald_data = read_italya_ald(file_path)

            # Initialize Subsections
            self._init_subsections()

            # 3. Map Top-Level Metadata
            self.system_name = ald_data.system_name
            self.start_timestamp = ald_data.start_timestamp
            self.raw_metadata = ald_data.metadata

            # 4. Map JSON configurations and lists
            meas_data = self.results[0].data
            meas_data.port_configurations = ald_data.port_configurations
            meas_data.precursor_doses = ald_data.precursor_doses
            meas_data.running_recipe = ald_data.running_rcp

            # 5. Process and Map Sensor Logs (Telemetry)
            if ald_data.communication_data is not None and not ald_data.communication_data.empty:
                df = ald_data.communication_data

                # Convert timestamps to datetime to calculate relative seconds
                # Format expected: DD.MM.YYYY HH:MM:SS
                df['datetime'] = pd.to_datetime(df['timestamp'], format="%d.%m.%Y %H:%M:%S", errors='coerce')

                # Drop rows where datetime parsing failed
                df = df.dropna(subset=['datetime'])

                if not df.empty:
                    start_time = df['datetime'].iloc[0]
                    df['rel_time_s'] = (df['datetime'] - start_time).dt.total_seconds()

                    # Group by sensor and create a SensorLog for each
                    meas_data.sensor_logs = []
                    for sensor_name, group in df.groupby('sensor'):
                        log = SensorLog()
                        log.sensor_name = sensor_name
                        log.time = group['rel_time_s'].to_numpy()
                        log.value = pd.to_numeric(group['value'], errors='coerce').to_numpy()
                        meas_data.sensor_logs.append(log)

        except Exception as e:
            if logger:
                logger.error(f'Error parsing Italya ALD log file: {e}')
            raise e

        super().normalize(archive, logger)


class RawFileALDData(EntryData):
    """Placeholder for the raw ALD file to point to the generated ELN."""

    m_def = Section(label='Raw ALD Log File')

    measurement = Quantity(
        type=ELNItalyaALD,
        a_eln=dict(component=ELNComponentEnum.ReferenceEditQuantity),
        description='The editable ELN archive generated from this raw file.',
    )


m_package.__init_metainfo__()