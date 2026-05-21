import os
import sys

# Tambahkan direktori root ke dalam sys.path agar import 'src' berjalan lancar
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.orchestrator import Orchestrator

def main():
    print("Memulai ScholarScout Pipeline...")
    orchestrator = Orchestrator()
    orchestrator.run_pipeline()

if __name__ == "__main__":
    main()
