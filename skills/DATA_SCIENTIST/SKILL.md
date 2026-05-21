# Data Scientist

## Profile
- **Duration:** 2-6 months (project-based)
- **Compute:** Cloud GPU (Colab Pro, AWS, or institutional cluster)
- **Budget:** $50-500 for compute and API costs
- **Scope:** End-to-end ML pipeline: data → model → evaluation → deployment-ready

## Constraints
- Must use publicly available datasets (or synthetic data generation)
- Code must be reproducible (Docker, requirements.txt, seed fixing)
- No access to proprietary/clinical data without explicit mention
- Prefer Python ecosystem (PyTorch, HuggingFace, scikit-learn)
- Results must include proper baselines and ablation studies

## Methodology Preferences
- Transfer learning and fine-tuning over training from scratch
- Benchmark-driven evaluation (standard metrics, standard splits)
- Emphasis on reproducibility and open-source tooling
- MLOps-aware: experiment tracking, model versioning

## Output Expectations
- Clean GitHub repository with README, requirements, and notebooks
- Trained model weights (or training script that reproduces them)
- Evaluation report with comparison to baselines
- Optional: blog post, Kaggle notebook, or HuggingFace model card

## Tools Ecosystem
- PyTorch / TensorFlow
- HuggingFace Transformers, Datasets, PEFT
- Weights & Biases / MLflow for tracking
- Docker for reproducibility
- Gradio / Streamlit for demos
