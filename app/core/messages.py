from dataclasses import dataclass

@dataclass
class AudioMessage:
    data: bytes
    sample_rate: int = 16000

@dataclass
class TextMessage:
    text: str
    is_final: bool = False

@dataclass
class InterruptionMessage:
    """Mensaje para señalizar que el usuario ha interrumpido el flujo actual."""
    pass
