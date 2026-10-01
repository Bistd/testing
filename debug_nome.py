from core.calculos import montar_sugestoes
from core.config import carregar_config

c = carregar_config()

# Busca com % (do jeito certo)
r1 = montar_sugestoes(1, '2026-09', c, filtro_busca='%coca%')
print(f"%coca%: {len(r1)}")

r2 = montar_sugestoes(1, '2026-09', c, filtro_busca='%mococa%')
print(f"%mococa%: {len(r2)}")

# Verifica se tem FL nesses
fl = [p for p in r2 if p.get('fora_de_linha', '').upper() == 'FL']
print(f"FL na busca: {len(fl)}")