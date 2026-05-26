import os
import sys

# Tambahkan direktori root ke dalam sys.path agar import 'src' berjalan lancar
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.orchestrator import Orchestrator

def main():
    mode = os.environ.get("SCOUT_MODE", "default")
    goal = os.environ.get("SCOUT_GOAL", "any")
    print(f"Starting ScholarScout Pipeline (mode={mode}, goal={goal})...")
    orchestrator = Orchestrator()
    
    # Auto-detect review mode from goal if SCOUT_MODE not explicitly set
    if mode == "review" or goal == "SYNTHESIS":
        topic = os.environ.get("SCOUT_CONTEXT", "")
        print(f"Routing to review pipeline (topic: {topic[:50]}...)")
        orchestrator.run_review_pipeline(topic=topic)
    else:
        print("Routing to default pipeline")
        orchestrator.run_pipeline()

if __name__ == "__main__":
    main()
