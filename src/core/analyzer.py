import textwrap
import re
import json
from typing import List

from src.core.models import Paper, TrendAnalysis
from src.core.llm import LLMClient
from src.core.config import Config

class TrendAnalyzer:
    """Analyzes research trends from a collection of papers using LLM."""
    
    KEYWORD_SEEDS = {
        "cs.AI":   ["agent","reasoning","planning","multimodal","alignment","safety"],
        "cs.LG":   ["federated","continual","few-shot","diffusion","efficiency","pruning"],
        "cs.CL":   ["llm","rag","hallucination","multilingual","chain-of-thought","benchmark"],
        "cs.CV":   ["3d","video","foundation model","detection","segmentation","generative"],
        "cs.RO":   ["manipulation","sim-to-real","locomotion","grasping","imitation"],
        "cs.CR":   ["adversarial","privacy","watermark","backdoor","differential privacy"],
        "cs.NE":   ["spiking","neuromorphic","evolutionary","neuro-symbolic"],
        "cs.SE":   ["code generation","testing","program synthesis","bug detection"],
        "cs.IR":   ["recommendation","retrieval","knowledge graph","rag","reranking"],
        "cs.HC":   ["usability","accessibility","interaction design","eye tracking"],
        "cs.DB":   ["query optimization","distributed database","graph database","streaming"],
        "cs.DC":   ["consensus","blockchain","serverless","edge computing"],
        "stat.ML": ["bayesian","uncertainty","causal","ood","conformal prediction"],
        "math.OC": ["control","optimization","mpc","stochastic","convergence"],
        "math.ST": ["hypothesis testing","nonparametric","high-dimensional","time series"],
        "math.NA": ["finite element","numerical solver","approximation","mesh"],
        "math.CO": ["graph theory","combinatorial optimization","network flow"],
        "math.AP": ["differential equations","dynamical systems","modeling"],
        "eess.AS": ["speech","audio","music","noise","asr","tts","codec"],
        "eess.IV": ["medical imaging","mri","ct","segmentation","pathology"],
        "eess.SP": ["radar","lidar","sensor fusion","channel","signal processing"],
        "eng.civil": ["structural","concrete","earthquake","bridge","geotechnical"],
        "eng.mechanical": ["thermodynamics","fluid dynamics","vibration","manufacturing"],
        "eng.chemical": ["reactor","catalysis","separation","process control"],
        "eng.materials": ["nanomaterials","polymer","composite","alloy","thin film"],
        "eng.biomedical": ["prosthetics","tissue engineering","biosensor","implant"],
        "eng.environmental": ["water treatment","air quality","waste management","remediation"],
        "med.cardio": ["cardiac","arrhythmia","echocardiography","stent","heart failure"],
        "med.neuro": ["alzheimer","parkinson","epilepsy","stroke","neuroimaging"],
        "med.onco": ["tumor","chemotherapy","immunotherapy","biomarker","metastasis"],
        "med.pharma": ["drug delivery","clinical trial","pharmacokinetics","toxicology"],
        "med.public": ["epidemiology","vaccination","pandemic","health policy","screening"],
        "med.surgery": ["minimally invasive","robotic surgery","transplant","laparoscopic"],
        "med.radiology": ["ct scan","mri","ultrasound","pet","radiomics"],
        "med.genetics": ["gene therapy","crispr","hereditary","genome editing","mutation"],
        "med.pediatrics": ["neonatal","child development","pediatric oncology","vaccination"],
        "med.infectious": ["antibiotic resistance","viral","pathogen","vaccine","pandemic"],
        "q-bio.GN": ["genomics","single-cell","gene expression","crispr"],
        "q-bio.NC": ["eeg","fmri","brain-computer","connectome"],
        "q-bio.QM": ["drug discovery","protein folding","docking","molecular dynamics"],
        "bio.ecology": ["biodiversity","conservation","ecosystem","species interaction"],
        "bio.molecular": ["protein structure","gene regulation","rna","transcription"],
        "bio.microbio": ["microbiome","antibiotic","bacteria","phage","fermentation"],
        "bio.biotech": ["crispr","synthetic biology","biofuel","enzyme engineering"],
        "bio.marine": ["coral reef","ocean acidification","marine ecosystem","fisheries"],
        "physics.med-ph": ["radiotherapy","dosimetry","imaging","biophotonics"],
        "physics.optics": ["laser","fiber optics","photonic crystal","holography"],
        "physics.quantum": ["qubit","entanglement","quantum computing","quantum error"],
        "physics.astro": ["exoplanet","dark matter","gravitational wave","galaxy"],
        "physics.condensed": ["superconductor","topological","2d materials","magnetism"],
        "physics.nuclear": ["fission","fusion","isotope","accelerator"],
        "physics.plasma": ["tokamak","plasma confinement","fusion energy"],
        "chem.organic": ["synthesis","catalysis","reaction mechanism","stereochemistry"],
        "chem.inorganic": ["coordination","metal-organic","crystal structure"],
        "chem.analytical": ["spectroscopy","chromatography","mass spectrometry","sensor"],
        "chem.physical": ["thermodynamics","kinetics","surface chemistry","electrochemistry"],
        "chem.biochem": ["enzyme","metabolism","protein","lipid","carbohydrate"],
        "chem.computational": ["dft","molecular dynamics","force field","docking"],
        "soc.psychology": ["cognitive","behavior","mental health","perception","memory"],
        "soc.economics": ["market","inflation","trade","behavioral economics","fintech"],
        "soc.political": ["governance","democracy","policy","conflict","election"],
        "soc.sociology": ["inequality","migration","social network","urbanization"],
        "soc.education": ["e-learning","pedagogy","assessment","curriculum","mooc"],
        "soc.communication": ["social media","misinformation","journalism","digital"],
        "soc.law": ["regulation","compliance","intellectual property","privacy law"],
        "earth.climate": ["global warming","carbon","greenhouse","adaptation","mitigation"],
        "earth.geology": ["seismology","volcanic","mineral","tectonic","sediment"],
        "earth.ocean": ["ocean current","salinity","marine pollution","deep sea"],
        "earth.atmospheric": ["weather prediction","aerosol","ozone","precipitation"],
        "earth.remote": ["satellite","lidar","gis","land use","vegetation index"],
        "earth.sustainability": ["renewable energy","solar","wind","circular economy"],
        "agri.crop": ["plant breeding","precision agriculture","drought resistance","yield"],
        "agri.animal": ["livestock","poultry","feed efficiency","animal welfare"],
        "agri.food": ["food safety","preservation","fermentation","nutrition"],
        "agri.forestry": ["deforestation","reforestation","carbon sequestration","timber"],
        "agri.aquaculture": ["fish farming","shrimp","water quality","feed"],
    }

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def analyze(self, papers: List[Paper], category: str) -> TrendAnalysis:
        # Use all papers passed in (orchestrator already caps the batch size)
        batch = papers[:30]  # Safety cap at 30 to avoid token overflow
        paper_list = "\n".join(
            f"[{i+1}] {p.title}\n    {p.abstract[:250]}"
            for i, p in enumerate(batch)
        )
        
        prompt = textwrap.dedent(f"""
            You are a research intelligence analyst specializing in {category}.
            Analyze these {len(batch)} recent papers and identify actionable research signals.

            Papers:
            {paper_list}

            Return a JSON object with exactly these keys:
            - "top_keywords": list of 5 dominant technical keywords/phrases (specific, not generic)
            - "emerging_methods": list of 3 novel methods, techniques, or architectures appearing in these papers
            - "research_gaps": list of 3 specific underexplored directions that NO paper above fully addresses (be concrete — name what's missing, not vague statements)
            - "methodology_patterns": list of 3 common methodological approaches used across these papers (e.g., "LoRA fine-tuning on domain-specific data", "contrastive pre-training + downstream transfer")
            - "representative_ids": list of 3 paper numbers (1-indexed) that best represent the current frontier

            Be SPECIFIC. Avoid generic phrases like "novel approach" or "further research needed."
            Name concrete techniques, datasets, and evaluation methods.

            Respond ONLY with valid JSON. No markdown fences, no explanation.
        """).strip()

        response = self.llm.call(prompt, task_type="trend_analysis")
        if response:
            cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
            try:
                parsed = json.loads(cleaned)
                rep_ids = parsed.get("representative_ids", [])
                
                ref_papers = []
                for p_idx in rep_ids:
                    try:
                        idx = int(p_idx) - 1
                        if 0 <= idx < len(batch):
                            ref_papers.append(batch[idx])
                    except (ValueError, TypeError):
                        # Try matching by ID string
                        for p in batch:
                            if str(p_idx) in p.id:
                                ref_papers.append(p)
                                break
                
                if not ref_papers:
                    ref_papers = batch[:3]
                
                return TrendAnalysis(
                    category=category,
                    paper_count=len(batch),
                    top_keywords=parsed.get("top_keywords", []),
                    emerging_methods=parsed.get("emerging_methods", []),
                    research_gaps=parsed.get("research_gaps", []),
                    methodology_patterns=parsed.get("methodology_patterns", []),
                    ref_papers=ref_papers
                )
            except Exception:
                pass

        # Fallback if LLM fails
        corpus = " ".join((p.title + " " + p.abstract).lower() for p in batch)
        seeds  = self.KEYWORD_SEEDS.get(category, [])
        found  = sorted([(kw, corpus.count(kw)) for kw in seeds if corpus.count(kw) > 0], key=lambda x: -x[1])
        
        return TrendAnalysis(
            category=category,
            paper_count=len(batch),
            top_keywords=[k for k, _ in found[:5]],
            emerging_methods=[k for k, _ in found[:2]],
            research_gaps=[],
            methodology_patterns=[],
            ref_papers=batch[:3]
        )
