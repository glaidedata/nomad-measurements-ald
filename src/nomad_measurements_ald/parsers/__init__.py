from nomad.config.models.plugins import ParserEntryPoint


class ALDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from nomad_measurements_ald.parsers.parser import ALDParser

        return ALDParser(**self.dict())


parser_entry_point = ALDParserEntryPoint(
    name='ALD Parser',
    description='Parser for Atomic Layer Deposition (ALD) log files.',
    mainfile_name_re=r'^.*\.(txt)$',
)