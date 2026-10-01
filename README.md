# Sistema de Compras — Cotação

App desktop (Tkinter + SQLite) para gerenciar o setor de compras de duas filiais
de uma franquia de supermercado.

## Estrutura

- `main.py` — ponto de entrada
- `config.json` — configurações
- `core/` — banco, importação, cálculos
- `ui/` — interface
- `dados_entrada/` — pasta onde você joga os arquivos `.xls`
  - `PRODUTOS/` — `Z CADASTRO.XLS` + `ZCAD.XLS`
  - `A-JAN/` ... `L-DEZ/` — movimento mensal
- `data/` — banco SQLite (criado automaticamente)
- `logs/` — logs de importação

## Como rodar

```bash
pip install -r requirements.txt
python main.py