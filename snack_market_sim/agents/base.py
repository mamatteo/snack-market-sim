"""
Base Agent — classe base per tutti gli agenti.

Principio 1: Il system prompt definisce chi è l'agente e cosa vuole. Mai come ottenerlo.
Principio 2: Contesto ricco, non prescrittivo.
Principio 3: Memoria attiva e verificabile.
"""

import json
import re
from abc import ABC, abstractmethod
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage


class BaseAgent(ABC):

    def __init__(self, agent_id: str, model: str = "qwen3:8b"):
        self.agent_id = agent_id
        self.llm = ChatOllama(model=model, temperature=0.7)
        self.episode_history: list[dict] = []  # memoria locale episodio corrente

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
        # Cerca blocco ```json ... ```
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Cerca { ... } direttamente
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Nessun JSON trovato nella risposta: {text[:200]}")

    def reset_episode(self):
        self.episode_history = []

    def add_to_history(self, entry: dict):
        self.episode_history.append(entry)
        # Mantieni solo le ultime 10 settimane (sliding window)
        if len(self.episode_history) > 10:
            self.episode_history = self.episode_history[-10:]

    def get_history_summary(self) -> str:
        if not self.episode_history:
            return "Nessuna storia recente."
        lines = ["Storia recente (ultime settimane):"]
        for entry in self.episode_history[-5:]:
            lines.append(f"  W{entry.get('week', '?')}: {entry.get('summary', '')}")
        return "\n".join(lines)
