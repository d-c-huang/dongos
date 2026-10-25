import copy,unittest
from p2_fixture_contract import INPUTS,validate_rounding,validate_errors
class ContractTests(unittest.TestCase):
 def rows(self):
  expected=[(True,0x100000,0x1000),(True,0x100000,0x1000),(True,0x100000,0x1000),(True,0x100000,0x2000),(True,0x12345000,0x3000),(True,0x100000,0x1000000),(True,0x100000,0x1001000),(True,0xfffffffff000,0x1000),(False,None,None),(False,None,None),(False,None,None),(False,None,None)]
  return {'schema':1,'cases':[dict(id=n,base=hex(b),size=hex(s),valid=v,physical=hex(p) if v else None,bytes=hex(z) if v else None) for (n,b,s),(v,p,z) in zip(INPUTS,expected)]}
 def test_known_boundary_answers(self):self.assertTrue(validate_rounding(self.rows()))
 def test_wrong_padding_overflow_and_duplicate_rejected(self):
  for index,field,value in [(3,'bytes','0x1000'),(6,'bytes','0x1000000'),(8,'valid',True),(1,'id','aligned-byte'),(0,'valid',1)]:
   data=self.rows();data['cases'][index][field]=value
   with self.assertRaises(AssertionError):validate_rounding(data)
 def errors(self):
  names=['Invalid','Authority','Forest','HardwareState','Held','Deadline','Capacity','Storage']
  source=''.join('pub error '+n+'='+hex(0x06150001+i)+';' for i,n in enumerate(names))
  data=dict(schema=1,module='mm.runtime_cache',errors=[dict(name=n,code=hex(0x06150001+i),meaning='明确错误原因') for i,n in enumerate(names)])
  return data,source
 def test_source_constants(self):
  data,source=self.errors();self.assertTrue(validate_errors(data,source))
 def test_bad_error_code_and_duplicate_rejected(self):
  data,source=self.errors();data['errors'][0]['code']='0x06150009'
  with self.assertRaises(AssertionError):validate_errors(data,source)
  data,source=self.errors();data['errors'][1]=copy.deepcopy(data['errors'][0])
  with self.assertRaises(AssertionError):validate_errors(data,source)
