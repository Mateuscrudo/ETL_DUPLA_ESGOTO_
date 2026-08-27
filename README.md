# ETL ESGOTO

## Estrutura

```text
ETL_ESGOTO/
├── main.py
├── ENTRADA/
├── ETL/
├── SAIDA/
└── LOG/
```

Coloque na pasta `ENTRADA`:
- um arquivo cujo nome contenha `ROTEIRO`;
- um arquivo cujo nome contenha `APPDEEP`.

O `main.py` localiza as bases automaticamente.

## Execução

Na raiz do projeto:

```powershell
python main.py
```

## Saídas

O processo gera:

```text
SAIDA/
├── CONSOLIDADO_ESGOTO.xlsx
└── base_consolidada.db
```

O Excel possui:
- `Base_Consolidada`
- `Fotos_Normalizadas`
- `Historico_Visitas`

O SQLite possui:
- `base_consolidada`
- `fotos_normalizadas`
- `historico_visitas`

## Regras implementadas

1. Matrícula presente nas duas bases: soma dos acumulados de visitas das duas fontes.
2. Dados principais: registro mais recente. Em empate, AppDeep tem prioridade.
3. Fotos: uma URL por linha e matrícula explícita.
4. Vários links em uma célula: cada link vira um registro separado.
5. Registros AppDeep marcados como `DUPLICADO` não entram na Base_Consolidada, mas permanecem no histórico.
