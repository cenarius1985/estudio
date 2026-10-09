"""Grafo de conocimiento ligero: entidades del dominio MRI detectadas por
diccionario (+ triples opcionales extraídas por LLM) y aristas de co-ocurrencia
por chunk. Se usa para expandir contexto en preguntas multi-salto.

OJO diseño: solo claves inequívocas (nada de "te", "us", "rm" sueltos, que en
español colisionan con palabras comunes). La cobertura fina la aporta BM25.
"""

from __future__ import annotations

import re

# clave (regex-ready, minúsculas) → nombre normalizado del nodo
VOCABULARIO: dict[str, str] = {
    # secuencias / técnicas
    "ute": "UTE",
    "ultrashort echo time": "UTE",
    "ultrashort te": "UTE",
    "zero echo time": "ZTE",
    "zte": "ZTE",
    "petra": "PETRA",
    "sprite": "SPRITE",
    "spi": "SPI",
    "epi": "EPI",
    "blipped epi": "blipped EPI",
    "compressed sensing": "compressed sensing",
    # contrastes / relaxometría
    r"t2\*": "T2*",
    "t2 estrella": "T2*",
    "t1": "T1",
    "t2": "T2",
    "t2 libre": "T2 libre",
    "myelin water": "agua de mielina",
    "agua de mielina": "agua de mielina",
    "relaxometria": "relaxometría",
    "relaxometry": "relaxometría",
    "bound pool": "bound pool",
    "magnetization transfer": "magnetización de transferencia",
    "magnetizacion de transferencia": "magnetización de transferencia",
    "densidad de protones": "densidad de protones",
    "proton density": "densidad de protones",
    # calidad de imagen
    "snr": "SNR",
    "signal[- ]to[- ]noise": "SNR",
    "cnr": "CNR",
    "contrast[- ]to[- ]noise": "CNR",
    "ruido": "ruido",
    "noise": "ruido",
    "artefacto": "artefacto",
    "artifact": "artefacto",
    "resolucion": "resolución",
    "resolution": "resolución",
    "voxel": "voxel",
    "fov": "FOV",
    "k[- ]space": "espacio k",
    "espacio k": "espacio k",
    "muestreo radial": "muestreo radial",
    "radial sampling": "muestreo radial",
    "reconstruccion": "reconstrucción",
    "reconstruction": "reconstrucción",
    # física / equipos
    "chemical shift": "chemical shift",
    "desplazamiento quimico": "chemical shift",
    "fat[- ]water": "fat-water",
    "water[- ]fat": "fat-water",
    "agua y grasa": "fat-water",
    "susceptibilidad": "susceptibilidad",
    "susceptibility": "susceptibilidad",
    "b0": "B0",
    "b1\\+": "B1",
    "echo time": "TE",
    "tiempo de eco": "TE",
    "repetition time": "TR",
    "tiempo de repeticion": "TR",
    "tesla": "Tesla",
    "3t": "3T",
    "1\\.5t": "1.5T",
    "7t": "7T",
    "siemens": "Siemens",
    "bruker": "Bruker",
    "philips": "Philips",
    "coil": "coil",
    "antena": "coil",
    # modalidades
    "resonancia magnetica": "MRI",
    "magnetic resonance": "MRI",
    "\\bmri\\b": "MRI",
    "ultrasonido": "ultrasonido",
    "ultrasound": "ultrasonido",
    "elastografia": "elastografía",
    "elastography": "elastografía",
    # tejidos / anatomía de la tesis
    "sutura": "sutura",
    "suture": "sutura",
    "tendon": "tendón",
    "tendón": "tendón",
    "ligamento": "ligamento",
    "menisco": "menisco",
    "cartilago": "cartílago",
    "cartilage": "cartílago",
    "hueso cortical": "hueso cortical",
    "cortical bone": "hueso cortical",
    "tejido blando": "tejido blando",
    "soft tissue": "tejido blando",
    "pulmon": "pulmón",
    "lung": "pulmón",
    "colageno": "colágeno",
    "collagen": "colágeno",
    "phantom": "phantom",
    "voluntario": "voluntario",
    "volunteer": "voluntario",
    "paciente": "paciente",
    "patient": "paciente",
    # análisis / ML
    "aprendizaje automatico": "machine learning",
    "machine learning": "machine learning",
    "deep learning": "deep learning",
    "red neuronal": "red neuronal",
    "neural network": "red neuronal",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "segmentacion": "segmentación",
    "segmentation": "segmentación",
}


def _patron(clave: str) -> re.Pattern:
    # \b no aplica tras caracteres no-palabra (*, +, .): el grupo se cierra igual
    return re.compile(r"(?<![a-z0-9])" + clave + r"(?![a-z0-9])", re.IGNORECASE)


_PATRONES = [( _patron(k), nombre) for k, nombre in VOCABULARIO.items()]


def entidades_en_texto(texto: str) -> list[str]:
    """Nodos (nombre normalizado) presentes en el texto, sin duplicados."""
    hallados: set[str] = set()
    for patron, nombre in _PATRONES:
        if patron.search(texto):
            hallados.add(nombre)
    return sorted(hallados)
