"""Byte-level oracle captured from the frozen post-T10 ArtifactBuilder."""
import json
from pathlib import Path
import unittest
from app.results.assembler import ArtifactBuilder
from tests.ultimate_serialization_vectors import cases


class UltimateSerializationCompatibilityTests(unittest.TestCase):
    def test_all_bytes_hashes_chunk_boundaries_and_ids_match_post_t10_vectors(self):
        frozen=json.loads((Path(__file__).parent/'fixtures/ultimate/t11-serialization-vectors.json').read_text())
        for name,(core,schema,rows) in cases().items():
            with self.subTest(name=name):
                builder=ArtifactBuilder(core)
                descriptor=builder.dataset('compatibility',schema,rows)
                self.assertEqual(descriptor.model_dump(mode='json'),frozen['cases'][name]['descriptor'])
                self.assertEqual([{'sha256':p.reference.content_sha256,'bytes':len(p.content),
                    'row_count':len(json.loads(p.content)['rows'])} for p in builder.parts],frozen['cases'][name]['parts'])
                self.assertEqual(sum(len(json.loads(p.content)['rows']) for p in builder.parts),len(rows))
