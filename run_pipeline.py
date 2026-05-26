import os
import sys

# Tambahkan direktori root ke dalam sys.path agar import 'src' berjalan lancar
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.orchestrator import Orchestrator

def main():
    print("Starting ScholarScout Pipeline...")
    mode = os.environ.get("SCOUT_MODE", "default")
    orchestrator = Orchestrator()
    
    if mode == "review":
        topic = os.environ.get("SCOUT_CONTEXT", "")
        orchestrator.run_review_pipeline(topic=topic)
    else:
        orchestrator.run_pipeline()

if __name__ == "__main__":
    main()
