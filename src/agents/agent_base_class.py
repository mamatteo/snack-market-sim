"""
Base Agent — classe base per tutti gli agenti.

Principio 1: Il system prompt definisce chi è l'agente e cosa vuole. Mai come ottenerlo.
Principio 2: Contesto ricco, non prescrittivo.
Principio 3: Memoria attiva e verificabile.

Memoria a breve termine (short-term memory):
    Ogni agente mantiene `short_term_memory`, una sliding window delle proprie ultime 10
    decisioni settimanali. È privata — non visibile agli altri agenti — e viene azzerata
    a inizio di ogni nuovo episodio. Permette all'agente di contestualizzare le decisioni
    correnti rispetto alle mosse recenti senza dipendere dalla memoria condivisa.

    La memoria a lungo termine (cross-episodio, condivisa) vive invece nel MarketMemoryGraph
    (memory/system_memory.py) e viene passata come `memory_context` a ogni chiamata decide().
"""

import json
import re
from abc import ABC, abstractmethod
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from config import SHORT_TERM_MEMORY_SIZE, SHORT_TERM_CONTEXT_SIZE


class BaseAgent(ABC):

    def __init__(self, agent_id: str, model: str = "qwen3:8b"):
        self.agent_id = agent_id
        self.llm = ChatOllama(model=model, temperature=0.7)
        self.short_term_memory: list[dict] = []  # memoria a breve termine: privata, per-episodio

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Chi è l'agente e cosa vuole. Mai come ottenerlo."""
        pass

    @abstractmethod
    def decide(self, world_state: str, memory_context: str, week: int) -> dict:
        """Prende una decisione dato lo stato del mondo e la memoria condivisa."""
        pass

    def _call_llm(self, user_message: str) -> str:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]
        response = self.llm.invoke(messages)
        return response.content

    def _extract_json(self, text: str) -> dict:
        """Estrae JSON dalla risposta del modello."""
        def _sanitize(s: str) -> str:
            # Rimuove + davanti ai numeri (non è JSON standard ma alcuni LLM lo producono)
            return re.sub(r'(?<!["\w])\+(\d)', r'\1', s)

        # Cerca blocco ```json ... ```
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(_sanitize(match.group(1)))
            except json.JSONDecodeError:
                pass

        # Fallback: estrai il blocco { } più esterno con stack di parentesi
        start = text.find("{")
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(_sanitize(text[start:i+1]))
                        except json.JSONDecodeError:
                            break
        raise ValueError(f"Nessun JSON valido trovato nella risposta: {text[:200]}")

    def reset_short_term_memory(self):
        """Azzera la memoria a breve termine. Chiamare a inizio di ogni nuovo episodio."""
        self.short_term_memory = []

    def add_to_short_term_memory(self, entry: dict):
        """Aggiunge una decisione alla memoria a breve termine (sliding window configurabile)."""
        self.short_term_memory.append(entry)
        if len(self.short_term_memory) > SHORT_TERM_MEMORY_SIZE:
            self.short_term_memory = self.short_term_memory[-SHORT_TERM_MEMORY_SIZE:]

    def get_short_term_context(self) -> str:
        """Serializza la memoria a breve termine in linguaggio naturale per il prompt dell'agente."""
        if not self.short_term_memory:
            return "Nessuna storia recente."
        lines = ["Storia recente (ultime settimane):"]
        for entry in self.short_term_memory[-SHORT_TERM_CONTEXT_SIZE:]:
            lines.append(f"  W{entry.get('week', '?')}: {entry.get('summary', '')}")
        return "\n".join(lines)
