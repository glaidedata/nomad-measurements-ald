from nomad.config.models.plugins import SchemaPackageEntryPoint


class ALDSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_measurements_ald.schema_packages.schema_package import m_package

        return m_package


schema_package_entry_point = ALDSchemaPackageEntryPoint(
    name='ALD Schema',
    description='Schema package for Atomic Layer Deposition (ALD) measurements.',
)