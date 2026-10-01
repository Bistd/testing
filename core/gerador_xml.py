"""
Gera o Excel simples (XML) pro ERP importar.
Colunas: A=codigo_interno, B=preco, C=quantidade. Sem cabeçalho.
"""
from pathlib import Path
import openpyxl


def gerar_xml_pedido(itens: list, caminho_destino: Path):
    """
    itens: [{codigo_interno, preco, qtd}, ...]
    """
    wb = openpyxl.Workbook()
    ws = wb.active

    for i, it in enumerate(itens, start=1):
        ws.cell(row=i, column=1, value=it["codigo_interno"])
        ws.cell(row=i, column=2, value=round(float(it["preco"]), 2))
        ws.cell(row=i, column=3, value=int(it["qtd"]))

    wb.save(caminho_destino)
    return caminho_destino