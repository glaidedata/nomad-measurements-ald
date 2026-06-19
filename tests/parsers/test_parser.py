import logging
from unittest.mock import MagicMock, patch

from nomad.datamodel.datamodel import EntryArchive

from nomad_measurements_ald.parsers.parser import ALDParser


def test_is_mainfile():
    """Test that the parser correctly gates ALD files based on extension and keywords."""
    parser = ALDParser()

    valid_content = (
        'System Name: Italya\nSystem Configurations: {}\nCommunication Data: None'
    )

    # Valid file and content
    assert parser.is_mainfile('test_data.txt', 'text/plain', b'', valid_content) is True

    # Invalid extension
    assert (
        parser.is_mainfile('test_data.csv', 'text/plain', b'', valid_content) is False
    )

    # Valid extension, but missing keywords
    invalid_content = 'Just some standard text without ALD markers.'
    assert (
        parser.is_mainfile('test_data.txt', 'text/plain', b'', invalid_content) is False
    )


@patch('nomad_measurements_ald.parsers.parser.create_archive')
def test_parse(mock_create_archive):
    """Test that the parser correctly instantiates the placeholder and links the ELN."""
    parser = ALDParser()
    archive = EntryArchive()

    # Mock the NOMAD server context to prevent file system crashes
    archive.m_context = MagicMock()
    archive.m_context.logger = logging.getLogger(__name__)

    # Mock the archive creation function to just return a dummy reference string
    mock_create_archive.return_value = '../upload/archive/dummy_id#data'

    # Run the parse method
    parser.parse('path/to/test_file.txt', archive, logging.getLogger(__name__))

    assert archive.data is not None
    assert archive.data.m_def.name == 'RawFileALDData'
    assert archive.data.measurement.m_proxy_value == '../upload/archive/dummy_id#data'
