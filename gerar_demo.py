"""Entradas inteiramente inventadas, sem leitura de dados externos."""
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

def gerar_demo():
    root=Path(__file__).resolve().parent / 'ENTRADA'
    root.mkdir(parents=True,exist_ok=True)
    paths=[root/'ROTEIRO_FICTICIO.xlsx',root/'APPDEEP_FICTICIO.xlsx']
    if any(p.exists() for p in paths):
        raise FileExistsError('Amostras já existem; não serão sobrescritas.')
    r=pd.DataFrame([
        ['DEM1001','01/10/2026',2,'Rua Fictícia A, 10','Bairro Exemplo','Pessoa Fictícia A','Galeria demo','Equipe Fictícia A','Executado Conferido'],
        ['DEM1002','02/10/2026',1,'Rua Fictícia B, 20','Bairro Exemplo','Pessoa Fictícia B',None,'Equipe Fictícia B','Cancelado'],
    ],columns=['Matricula','Dt. Execução','Qtd. Tentat.','Endereço','Bairro','Nome Completo','Foto(s)','Oficial','Status'])
    a=pd.DataFrame([
        ['DEM1001',None,'03/10/2026','09:00',3,'ORIGINAL','Rua Fictícia A, 11','Bairro Exemplo','Pessoa Fictícia A','Agente Fictício A','Adesão executada','https://example.invalid/esgoto1.png','https://example.invalid/registro1','REG-DEMO-1'],
        ['DEM1001',None,'04/10/2026','10:00',99,'DUPLICADO','Rua Ignorada, 0','Bairro Exemplo','Pessoa Duplicada','Agente Fictício A','Cancelado','https://example.invalid/ignorada.png',None,None],
        [None,'DEM1003','05/10/2026','11:00',1,'ORIGINAL','Rua Fictícia C, 30','Bairro Exemplo','Pessoa Fictícia C','Agente Fictício C','Não visitado','https://example.invalid/esgoto3.png',None,'REG-DEMO-3'],
    ],columns=['Matrícula DEEP','codigo_unico_deep','Data do registro','Hora do registro','visitas','Tipo Registro Visita','Endereço','Bairro','Nome completo','Nome do Agente','Situação Campo','Foto demo','Link Backoffice','Code Deep'])
    r.to_excel(paths[0],sheet_name='Planilha1',index=False)
    wb=load_workbook(paths[0]);wb['Planilha1']['G2'].hyperlink='https://example.invalid/galeria1';wb.save(paths[0]);wb.close()
    a.to_excel(paths[1],sheet_name='Sheet1',index=False)
    print('Entradas fictícias de Esgoto criadas.')

if __name__=='__main__': gerar_demo()
