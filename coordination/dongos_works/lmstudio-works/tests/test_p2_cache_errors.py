import json,unittest
from pathlib import Path
from p2_fixture_contract import validate_errors
class CacheErrorsTests(unittest.TestCase):
 def test_lm_errors_match_production(self):
  works=Path(__file__).resolve().parents[2]
  root=works if (works/'kernel').is_dir() else works.parents[1]/'code'
  data=json.loads((works/'lmstudio-works/fixtures/p2-cache-errors.json').read_text(encoding='utf-8-sig'))
  self.assertTrue(validate_errors(data,(root/'kernel/mm/runtime_cache.dg').read_text(encoding='utf-8')))
