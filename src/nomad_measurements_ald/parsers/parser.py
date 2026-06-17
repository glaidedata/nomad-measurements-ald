from nomad.datamodel.context import ServerContext
from nomad.datamodel.datamodel import EntryArchive
from nomad.parsing.parser import MatchingParser
from nomad_measurements.utils import create_archive

from nomad_measurements_ald.schema_packages.schema_package import (
    ELNItalyaALD,
    RawFileALDData,
)


class ALDParser(MatchingParser):
    def is_mainfile(
        self,
        filename: str,
        mime: str,
        buffer: bytes,
        decoded_buffer: str,
        compression: str = None,
    ) -> bool:
        """Gatekeeper for ALD files."""

        filename_lower = filename.lower()

        # 1. Italya ALD Check (.txt)
        if filename_lower.endswith('.txt'):
            if decoded_buffer and ('System Name' in decoded_buffer and 'System Configurations' in decoded_buffer and 'Communication Data' in decoded_buffer):
                return True

        return False

    def parse(
        self,
        mainfile: str,
        archive: EntryArchive,
        logger=None,
        child_archives=None,
    ) -> None:
        logger = logger or archive.m_context.logger

        # Extract the filename, handling server context paths correctly
        data_file = mainfile.rsplit('/', maxsplit=1)[-1]
        if isinstance(archive.m_context, ServerContext):
            data_file = mainfile.split('/raw/', 1)[1]

        filename_lower = data_file.lower()

        # Route to the correct Schema based on the file extension
        if filename_lower.endswith('.txt'):
            entry = ELNItalyaALD()
        else:
            logger.error(f'Unsupported ALD file format: {data_file}')
            return

        # Assign the file name to the entry
        entry.data_file = data_file

        # Create the separate editable .archive.json file to preserve ELN edits
        archive_name = f'{"".join(data_file.split(".")[:-1])}.archive.json'
        eln_ref = create_archive(entry, archive, archive_name)

        # Link the raw .txt file to the generated ELN to prevent crashes and duplication
        archive.data = RawFileALDData(measurement=eln_ref)