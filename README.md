> **Cópia preparada com dados fictícios.** As planilhas em ENTRADA são exemplos inventados, gerados por `gerar_demo.py`; nenhum dado operacional foi copiado. Consulte [origem dos dados](docs/DADOS_FICTICIOS.md) e [validação desta cópia](VALIDACAO.md). O projeto interno permanece separado.

## Executar os exemplos incluídos

As entradas sintéticas já estão incluídas. Instale `requirements.txt` e execute `python -X utf8 main.py` na raiz. Para Água e Obra, use `$env:EXECUCAO_AGENTE = "1"` antes de executar para dispensar interação. `gerar_demo.py` documenta e reproduz a criação das entradas, mas recusa sobrescrevê-las; use uma cópia vazia para regenerar.

# ETL ESGOTO

Consolida as visitas do Roteiro e do AppDeep para consulta cadastral no aplicativo.
A limpeza acontece em memória e afeta somente as saídas. Os Excel de ENTRADA nunca são editados pelo ETL.

## Entrada e execução

Coloque em `ENTRADA/` um Excel cujo nome contenha `ROTEIRO` e outro cujo nome contenha `APPDEEP`.
Deve existir apenas um arquivo de cada tipo. Use `.xlsx` ou `.xlsm`.
O Roteiro deve ter a aba `Planilha1`; o AppDeep, `Sheet1`.
Os nomes das colunas são validados antes do processamento, incluindo `Situação Campo` e `Hora do registro` no AppDeep.

Dependências: Python, pandas, numpy e openpyxl.
Na raiz do projeto:

```powershell
python -X utf8 main.py
```

O modo UTF-8 permite exibir as mensagens em terminais Windows.
Há leitura compartilhada, sem escrita, para arquivos abertos no Excel que permitam esse acesso.
É recomendável salvar as alterações no Excel antes da execução: o ETL lê o conteúdo gravado em disco.

## Saídas

- `SAIDA/CONSOLIDADO_ESGOTO.xlsx`: abas `Base_Consolidada`, `Fotos_Normalizadas` e `Historico_Visitas`.
- `SAIDA/base_esgoto.db`: tabelas `base_consolidada`, `fotos_normalizadas` e `historico_visitas`.
- `LOG/execucao_etl.txt`: quantidades, exclusões, campos ausentes e resultado da execução.

O banco atual é **base_esgoto.db**. O arquivo antigo `base_consolidada.db`, se existir, não é atualizado por este código.
As saídas atuais são substituídas em cada execução. Faça backup antes de alterações no código ou de substituir resultados que precisem ser preservados.
O SQLite é gerado em arquivo temporário, passa pelo `PRAGMA integrity_check` e só depois substitui o destino.
Excel e SQLite não são publicados como uma transação única: confira o log após cada execução.
O log só registra `STATUS=SUCESSO` depois da geração das duas saídas; exceções registram `STATUS=FALHA` e são propagadas.

## Regras de negócio

### Identificação e duplicados

1. `Matrícula DEEP` prevalece sobre `codigo_unico_deep`, pois corrige a identificação anterior. O código único só é usado quando a matrícula está vazia.
2. Matrículas são tratadas como chaves de texto, com espaços externos removidos e letras maiúsculas.
3. AppDeep com `Tipo Registro Visita = duplicado`, ignorando maiúsculas e espaços externos, representa envio repetido pelo agente. É excluído da base, visitas, histórico e fotos, somente durante o processamento.
4. Visitas distintas com a mesma matrícula não são excluídas por esse motivo.

### Registro principal e visitas

1. Selecionar o registro mais recente de cada fonte para cada matrícula.
2. No AppDeep, usar `Hora do registro` para desempatar a mesma data. A hora é auxiliar e não aparece na consulta cadastral. Hora vazia ou inválida usa zero na ordenação.
3. Em empate completo dentro da fonte, a última linha do arquivo prevalece, com ordenação estável.
4. Entre Roteiro e AppDeep, escolher o registro mais recente; em igualdade de data, AppDeep prevalece.
5. Nome, endereço, bairro e agente acompanham integralmente o registro escolhido, inclusive campos vazios. Não recuperar dados de registros anteriores ou da outra fonte.
6. Visitas = acumulado do registro mais recente do Roteiro + acumulado do registro mais recente do AppDeep. As fontes representam períodos independentes da transição de sistemas. Não usar o maior acumulado histórico nem contar linhas do histórico para esse total.
7. Fonte ausente ou acumulado numérico ausente mantém contribuição zero, conforme o tratamento existente.
8. Mantida a limpeza existente de endereço: remover identificador inicial Cantagalo (CG/CGN) ou hífen solto inicial, sem completar o cadastro.

### Status

Primeiro converter os status do Roteiro em memória; depois selecionar a fonte mais recente.

| Status no Roteiro | Resultado |
| --- | --- |
| Impedimento Campo | Adesão executada |
| Pendente Validação | Adesão executada |
| Executado Conferido | Adesão executada |
| Cancelado | Cancelado |
| Impedimento Finalizado | Status tentativa (T3) |
| Programado / Disp. p/ programação | Último status preenchido em T3, T2, T1; sem status, Não visitado |
| Demais valores | Preservados |

Mantida a regra existente de `Impedimento Finalizado`: se T3 estiver vazio, o status fica vazio. Não há preenchimento automático por T2/T1 nessa condição.
No AppDeep, usar **Situação Campo**; quando vazio, preencher **Adesão executada**.
O status final acompanha a fonte principal escolhida, inclusive quando ela é exclusivamente AppDeep.

### Histórico de visitas

- Cada tentativa T1/T2/T3 do Roteiro com data, status ou equipe preenchidos vira uma linha, com sua própria data, status e equipe/agente.
- Tentativas sem informação não geram linha. Campos ausentes não são inventados.
- Registros do Roteiro convertidos para `Adesão executada` também preservam a execução, com `Dt. Execução`, status convertido e agente responsável. Isso mantém a visita de execução além das tentativas anteriores.
- Quando não existem tentativas, preservar a linha original do Roteiro como `REGISTRO` ou `EXECUÇÃO`.
- AppDeep: uma linha por registro não duplicado, com data, Situação Campo normalizada e Nome do Agente.
- A coluna `Status` representa a situação da visita. `Status do Registro` identifica o registro como `ORIGINAL`; `Tentativa` distingue T1/T2/T3, EXECUÇÃO e REGISTRO.
- `Visitas` no histórico vale 1 por linha. O total cadastral vem dos acumulados mais recentes, não da soma desse histórico.
- Registros AppDeep sem identificação permanecem no histórico, são contabilizados no log e não entram na base cadastral nem nas fotos.

### Fotos

- Fotos de envios AppDeep marcados como duplicados são excluídas.
- Fotos válidas de visitas anteriores permanecem disponíveis, independentemente da escolha do cadastro mais recente.
- AppDeep: colunas com `foto` no nome, com URLs separadas por quebra de linha.
- Roteiro: hyperlink da coluna `Foto(s)`, identificado como `Galeria`.
- Cada matrícula + URL aparece uma vez; mantido o critério existente de primeira ocorrência.
- URLs como texto sem hyperlink no Roteiro, fórmulas HYPERLINK e links separados somente por espaço/ponto e vírgula não são desdobrados pelo extrator atual.

## Colunas da consulta cadastral e rastreabilidade

`Matrícula`, `Endereço`, `Nome do Morador`, `Bairro`, `Data de Execução`, `Quantidade de Visitas`, `status`, `Agente Responsável`, `Origem dos Dados`.
Essas nove colunas são acompanhadas por quatro campos de rastreabilidade, totalizando **13 colunas** exportadas na base cadastral:

- `origem_adesao`: fonte do registro escolhido, `APPDEEP` ou `ROTEIRO`; difere de `Origem dos Dados`, que indica presença nas fontes.
- `data_origem_adesao`: data do registro escolhido, a mesma usada em `Data de Execução`.
- `link_appdeep`: valor de `Link Backoffice` somente quando a fonte escolhida é AppDeep e o link possui esquema HTTP/HTTPS e hostname. Não é construído por matrícula.
- `registro_appdeep`: identificação de `Code Deep` do registro AppDeep escolhido; fica ausente quando a fonte é Roteiro.

O histórico possui campos próprios, incluindo `link_appdeep` e `registro_appdeep` nos registros AppDeep não duplicados. Linhas do Roteiro não recebem esses links ou identificadores. Não há validação de disponibilidade dos links nem geração automática de URLs.

## Testes

```powershell
python -X utf8 -m unittest discover -s tests -v

# Diagnóstico manual interno não incluído nesta cópia.
```

Os sete testes automatizados verificam acumulados mais recentes, data/hora, status e empate, exclusão completa dos duplicados, preservação de campos vazios, tentativas com agentes e registro de falha no log.
O diagnóstico manual interno `teste_etl_esgoto.py` não integra esta cópia. Foi acrescentado `tests/test_demo.py`, totalizando oito testes executados com sucesso nesta preparação.

## Alterações e validação em 07/10/2026

Foi criado e conferido o backup `BACKUP/antes_limpeza_verificado_20261007` antes das alterações.
O backup preserva os códigos, README, consulta de teste, saídas anteriores, log e hashes SHA-256 das duas entradas.
Há checkpoints adicionais para ajustes de horário e documentação.

Resultado histórico documentado em 07/10/2026, com as entradas utilizadas naquela validação. Os números abaixo não são metas impostas pelo código nem foram reexecutados na revisão documental de 13/10/2026:

| Medida | Quantidade |
| --- | ---: |
| Matrículas consolidadas | 10.289 |
| Fotos normalizadas | 110.975 |
| Histórico total | 20.657 |
| Histórico Roteiro | 9.332 |
| Histórico AppDeep | 11.325 |
| Envios duplicados excluídos | 178 |
| Matrículas com quantidade de visitas alterada | 41 |

Todos os dados do Excel gerado foram comparados com o SQLite. O SQLite também foi comparado integralmente com os dados processados em memória e passou na verificação de integridade.
As visitas e a seleção de status foram conferidas para todas as matrículas por uma seleção independente dos registros mais recentes.
As duas entradas mantiveram os mesmos hashes SHA-256 antes e depois.

O log final contém `STATUS=SUCESSO`, zero datas e status ausentes no histórico, duas linhas do histórico sem matrícula e 361 status ausentes na base cadastral.
Os status cadastrais ausentes continuam expostos para revisão da origem; não foram substituídos por uma regra de negócio não autorizada.

## Revisão documental em 13/10/2026

Conferência estática dos módulos locais: entradas, regras de seleção, visitas, status, histórico, fotos e exportações. Atualizados os campos de rastreabilidade da base e do histórico. Não foram executados o ETL, os testes ou as bases de produção nesta revisão. Nenhuma regra de negócio foi alterada.
