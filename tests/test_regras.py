import sys, unittest
from pathlib import Path
import pandas as pd
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from ETL.consolidar import consolidar
from ETL.ler_bases import status_consolidado, horario_ordenacao
from ETL.processar_fotos import processar_fotos
from unittest.mock import patch

def roteiro(**values):
 row={'_mat':'X','_dt':pd.Timestamp('2026-01-01'),'_vis':9,'_status':'Adesão executada','_agent':'R','Endereço':'RUA R','Bairro':'R','Nome Completo':'R'}
 row.update(values); return row
def app(**values):
 row={'_mat':'X','_dt':pd.Timestamp('2026-01-02'),'_ord':pd.Timestamp('2026-01-02 08:00'),'_vis':8,'_status':'Recusa','_dup':False,'Nome do Agente':'A','Endereço':None,'Bairro':None,'Nome completo':None}
 row.update(values); return row
class Rules(unittest.TestCase):
 def test_latest_accumulated_not_max(self):
  r=pd.DataFrame([roteiro(),roteiro(_dt=pd.Timestamp('2026-01-03'),_vis=2)])
  a=pd.DataFrame([app(),app(_dt=pd.Timestamp('2026-01-04'),_ord=pd.Timestamp('2026-01-04'),_vis=1)])
  b,h=consolidar(r,a); self.assertEqual(b.iloc[0]['Quantidade de Visitas'],3)
 def test_time_status_and_no_old_fallback(self):
  a=pd.DataFrame([app(_ord=pd.Timestamp('2026-01-02 16:00'),_vis=2),app(_ord=pd.Timestamp('2026-01-02 08:00'),_vis=8,Endereço='VELHO')])
  b,h=consolidar(pd.DataFrame([roteiro()]),a)
  self.assertEqual(b.iloc[0]['Quantidade de Visitas'],11)
  self.assertEqual(b.iloc[0]['status'],'Recusa'); self.assertIsNone(b.iloc[0]['Endereço'])
  self.assertNotIn('_ord',b.columns); self.assertEqual(len(b.columns),13)
  self.assertTrue({'origem_adesao','data_origem_adesao','link_appdeep','registro_appdeep'}.issubset(b.columns))
 def test_duplicate_excluded_everywhere(self):
  a=pd.DataFrame([app(),app(_mat='DUP_ONLY',_dup=True,_vis=100)])
  b,h=consolidar(pd.DataFrame([roteiro()]),a)
  self.assertNotIn('DUP_ONLY',b['Matrícula'].tolist()); self.assertNotIn('DUP_ONLY',h['Matrícula'].tolist())
  class Cell:
   value=None
  class Sheet:
   max_row=1; max_column=3
   def cell(self,row,col):
    c=Cell();c.value=['Foto(s)','Matricula','Dt. Execução'][col-1];return c
  class Book:
   def __getitem__(self,key): return Sheet()
   def close(self): pass
  a['Foto teste']=['https://original','https://duplicado']
  with patch('ETL.processar_fotos.ler_bytes',return_value=b''),patch('ETL.processar_fotos.load_workbook',return_value=Book()):
   f=processar_fotos(Path('fake'),a)
  self.assertEqual(f.URL.tolist(),['https://original'])
 def test_attempts_date_status_agent(self):
  row=roteiro(_status='Recusa',**{'Data tentativa (T1)':'01/01/2026','Status tentativa (T1)':'Ausente','Equipe (T1)':'E1','Data tentativa (T2)':'02/01/2026','Status tentativa (T2)':'Recusa','Equipe (T2)':'E2'})
  b,h=consolidar(pd.DataFrame([row]),pd.DataFrame([app()]))
  hr=h[h.Origem=='ROTEIRO'];self.assertEqual(len(hr),2)
  self.assertEqual(hr.Status.tolist(),['Ausente','Recusa']);self.assertEqual(hr.Agente.tolist(),['E1','E2'])
 def test_conversion_then_latest_and_tie(self):
  for v in ['Impedimento Campo','Pendente Validação','Executado Conferido']:
   self.assertEqual(status_consolidado(pd.Series({'Status':v})),'Adesão executada')
  b,h=consolidar(pd.DataFrame([roteiro()]),pd.DataFrame([app(_dt=pd.Timestamp('2026-01-01'))]))
  self.assertEqual(b.iloc[0]['status'],'Recusa')
  b,h=consolidar(pd.DataFrame([roteiro(_dt=pd.Timestamp('2026-01-03'))]),pd.DataFrame([app()]))
  self.assertEqual(b.iloc[0]['status'],'Adesão executada')
 def test_hours(self):
  from datetime import time
  self.assertEqual(horario_ordenacao(time(13,20)),pd.Timedelta(hours=13,minutes=20))
  self.assertEqual(horario_ordenacao(.5),pd.Timedelta(hours=12))
  self.assertEqual(horario_ordenacao('17:08'),pd.Timedelta(hours=17,minutes=8))
 def test_failure_logged(self):
  import main
  with patch.object(main,'executar',side_effect=ValueError('falha simulada')),patch.object(main,'salvar_relatorio') as log:
   with self.assertRaises(ValueError):main.main()
   self.assertIn('STATUS=FALHA',log.call_args.args[0][0])
if __name__=='__main__': unittest.main(verbosity=2)
