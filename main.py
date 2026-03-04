"""
Agentic Category Management — entry point.

Uso:
    python main.py                    # episodio 1
    python main.py --episodes 10      # 10 episodi consecutivi
    python main.py --episode 5        # episodio specifico
    python main.py --model qwen3:14b  # modello diverso
"""

import argparse
import time
from rich.console import Console
from config import DEFAULT_MODEL

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Agentic Category Management")
    parser.add_argument("--episode", type=int, default=None, help="Episodio specifico da girare")
    parser.add_argument("--episodes", type=int, default=1, help="Numero di episodi consecutivi")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Modello Ollama da usare")
    parser.add_argument("--start-from", type=int, default=1, help="Episodio di partenza")
    args = parser.parse_args()

    from src.orchestrator.graph import run_episode

    if args.episode is not None:
        # Esegui un episodio specifico
        start = time.time()
        run_episode(args.episode, args.model)
        elapsed = time.time() - start
        console.print(f"\n[dim]Episodio completato in {elapsed:.1f}s[/dim]")
    else:
        # Esegui N episodi consecutivi
        for i in range(args.episodes):
            episode_num = args.start_from + i
            start = time.time()
            run_episode(episode_num, args.model)
            elapsed = time.time() - start
            console.print(f"\n[dim]Episodio {episode_num} completato in {elapsed:.1f}s[/dim]")
            if i < args.episodes - 1:
                console.print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
