import json,unittest
from pathlib import Path
from p2_fixture_contract import validate_rounding
class GoldenVectorsTests(unittest.TestCase):
 def test_lm_vectors(self):
  path=Path(__file__).resolve().parents[1]/'fixtures/p2-gop-rounding.json'
  self.assertTrue(validate_rounding(json.loads(path.read_text(encoding='utf-8-sig'))))
