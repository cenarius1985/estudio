#!/usr/bin/env python3
"""Copia docs/vault/*.md al vault oficial de Obsidian DATACEF cuando la
unidad G: (Google Drive) está montada. Idempotente y seguro (no borra nada).

Vault: G:\\Mi unidad\\DATACEF\\DOCUMENTACION-PROYECTOS\\ESTUDIO-DOCTORADO-DATACEF
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "docs" / "vault"
VAULT = Path("G:/Mi unidad/DATACEF/DOCUMENTACION-PROYECTOS/ESTUDIO-DOCTORADO-DATACEF")


def main() -> int:
    if not ORIGEN.is_dir():
        print("No hay documentos en docs/vault todavía.")
        return 0
    if not VAULT.parent.exists():
        print("❌ La unidad G: (Google Drive) no está montada. Ábrela y reintenta.")
        return 1

    VAULT.mkdir(parents=True, exist_ok=True)
    copiados = []
    for md in ORIGEN.glob("*.md"):
        destino = VAULT / md.name
        if destino.exists() and destino.read_text(encoding="utf-8") == md.read_text(encoding="utf-8"):
            continue  # sin cambios
        shutil.copy2(md, destino)
        copiados.append(md.name)

    if copiados:
        print("✅ Sincronizados al vault:", ", ".join(copiados))
    else:
        print("✅ Vault ya estaba al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
