"""
Migrações incrementais do banco (executadas na inicialização).
"""
from core.database import conectar


def aplicar_migracoes():
    """
    Aplica migrações necessárias. Seguro rodar várias vezes.
    Como estamos começando um banco novo, não há migrações no momento.
    """
    # Reservado para futuras migrações
    pass