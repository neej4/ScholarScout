"""
Unit tests for ImplementationFinder module.

Tests keyword extraction, source routing, API query methods (mocked),
and the overall find() orchestration.
"""

import unittest
from unittest.mock import patch, MagicMock
import json

from src.core.impl_finder import ImplementationFinder, IMPL_ROUTES
from src.core.config import Config


class TestImplFinderRouting(unittest.TestCase):
    """Test category → source routing logic."""

    def test_all_categories_have_routes(self):
        """Every category prefix should have a route defined."""
        expected = {"cs", "stat", "eess", "med", "bio", "q-bio",
                    "physics", "eng", "chem", "math", "soc", "earth", "agri"}
        self.assertEqual(set(IMPL_ROUTES.keys()), expected)

    def test_cs_routes_include_core_sources(self):
        """CS categories should include PwC, GitHub, HuggingFace."""
        routes = IMPL_ROUTES["cs"]
        self.assertIn("paperswithcode", routes)
        self.assertIn("github", routes)
        self.assertIn("huggingface", routes)

    def test_med_routes_include_clinicaltrials(self):
        """Medical categories should include ClinicalTrials."""
        routes = IMPL_ROUTES["med"]
        self.assertIn("clinicaltrials", routes)

    def test_chem_routes_include_chembl(self):
        """Chemistry categories should include ChEMBL."""
        routes = IMPL_ROUTES["chem"]
        self.assertIn("chembl", routes)

    def test_bio_routes_include_uniprot(self):
        """Biology categories should include UniProt."""
        routes = IMPL_ROUTES["bio"]
        self.assertIn("uniprot", routes)

    def test_physics_routes_include_zenodo(self):
        """Physics categories should include Zenodo."""
        routes = IMPL_ROUTES["physics"]
        self.assertIn("zenodo", routes)

    def test_earth_routes_include_kaggle(self):
        """Earth science categories should include Kaggle."""
        routes = IMPL_ROUTES["earth"]
        self.assertIn("kaggle", routes)

    def test_all_routes_have_pypi(self):
        """All categories should include PyPI (Python is universal)."""
        for cat, routes in IMPL_ROUTES.items():
            self.assertIn("pypi", routes, f"{cat} missing pypi")


class TestImplFinderKeywords(unittest.TestCase):
    """Test keyword extraction logic."""

    def setUp(self):
        self.finder = ImplementationFinder()

    def test_basic_keyword_extraction(self):
        """Should extract meaningful words from title."""
        kw = self.finder._build_keywords(
            "Federated Learning for Medical Image Segmentation",
            "", ""
        )
        self.assertIn("federated", kw)
        self.assertIn("learning", kw)
        self.assertIn("medical", kw)
        self.assertIn("image", kw)
        self.assertIn("segmentation", kw)

    def test_stopwords_removed(self):
        """Common stopwords should be filtered out."""
        kw = self.finder._build_keywords(
            "A Novel Approach for the Detection of Anomalies",
            "", ""
        )
        self.assertNotIn("a", kw)
        self.assertNotIn("for", kw)
        self.assertNotIn("the", kw)
        self.assertNotIn("of", kw)
        self.assertNotIn("novel", kw)
        self.assertNotIn("approach", kw)

    def test_methodology_included(self):
        """Keywords from methodology should be included."""
        kw = self.finder._build_keywords(
            "Test Title",
            "Use transformer architecture with attention mechanism",
            ""
        )
        self.assertIn("transformer", kw)
        self.assertIn("architecture", kw)
        self.assertIn("attention", kw)

    def test_max_keywords_limited(self):
        """Should return at most 6 keywords."""
        kw = self.finder._build_keywords(
            "One Two Three Four Five Six Seven Eight Nine Ten",
            "Eleven Twelve Thirteen", ""
        )
        self.assertLessEqual(len(kw), 6)

    def test_deduplication(self):
        """Duplicate words should be removed."""
        kw = self.finder._build_keywords(
            "Deep Learning Deep Networks Learning",
            "", ""
        )
        self.assertEqual(kw.count("deep"), 1)
        self.assertEqual(kw.count("learning"), 1)

    def test_short_words_filtered(self):
        """Words shorter than 3 chars should be filtered."""
        kw = self.finder._build_keywords("AI ML NLP Deep Learning", "", "")
        self.assertNotIn("ai", kw)
        self.assertNotIn("ml", kw)
        self.assertIn("nlp", kw)
        self.assertIn("deep", kw)


class TestImplFinderCategoryPrefix(unittest.TestCase):
    """Test category prefix extraction."""

    def setUp(self):
        self.finder = ImplementationFinder()

    def test_standard_category(self):
        self.assertEqual(self.finder._extract_category_prefix("cs.AI"), "cs")

    def test_nested_category(self):
        self.assertEqual(self.finder._extract_category_prefix("q-bio.BM"), "q-bio")

    def test_empty_field_defaults_to_cs(self):
        self.assertEqual(self.finder._extract_category_prefix(""), "cs")

    def test_uppercase_normalized(self):
        self.assertEqual(self.finder._extract_category_prefix("CS.AI"), "cs")


class TestImplFinderRepoName(unittest.TestCase):
    """Test GitHub repo name extraction from URLs."""

    def setUp(self):
        self.finder = ImplementationFinder()

    def test_standard_github_url(self):
        self.assertEqual(
            self.finder._extract_repo_name("https://github.com/huggingface/transformers"),
            "huggingface/transformers"
        )

    def test_github_url_with_path(self):
        self.assertEqual(
            self.finder._extract_repo_name("https://github.com/org/repo/tree/main/src"),
            "org/repo"
        )

    def test_non_github_url(self):
        url = "https://gitlab.com/some/repo"
        self.assertEqual(self.finder._extract_repo_name(url), url)


class TestImplFinderPyPICandidates(unittest.TestCase):
    """Test PyPI candidate package name generation."""

    def setUp(self):
        self.finder = ImplementationFinder()

    def test_known_keywords_map_to_packages(self):
        """Known ML keywords should map to well-known packages."""
        candidates = self.finder._build_pypi_candidates(["deep", "learning"])
        self.assertIn("torch", candidates)

    def test_hyphenated_combinations(self):
        """Should generate hyphenated keyword combinations."""
        candidates = self.finder._build_pypi_candidates(["federated", "learning", "privacy"])
        self.assertIn("federated-learning", candidates)

    def test_max_candidates_capped(self):
        """Should return at most 10 candidates."""
        candidates = self.finder._build_pypi_candidates(
            ["deep", "learning", "neural", "network", "transformer", "attention"]
        )
        self.assertLessEqual(len(candidates), 10)

    def test_no_duplicates(self):
        """Candidate list should have no duplicates."""
        candidates = self.finder._build_pypi_candidates(["machine", "learning"])
        self.assertEqual(len(candidates), len(set(candidates)))


class TestImplFinderPapersWithCode(unittest.TestCase):
    """Test Papers With Code query method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_successful_query(self, mock_http):
        """Should return repos when paper is found."""
        # First call: paper search
        mock_http.side_effect = [
            {"results": [{"id": "attention-is-all-you-need"}]},
            {"results": [
                {"url": "https://github.com/tensorflow/tensor2tensor", "stars": 15000, "framework": "TensorFlow"},
                {"url": "https://github.com/huggingface/transformers", "stars": 120000, "framework": "PyTorch"},
            ]}
        ]

        repos = self.finder._query_paperswithcode("Attention Is All You Need")
        self.assertEqual(len(repos), 2)
        # Should be sorted by stars descending
        self.assertEqual(repos[0]["stars"], 120000)
        self.assertEqual(repos[0]["source"], "paperswithcode")

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_paper_not_found(self, mock_http):
        """Should return empty list when paper not found."""
        mock_http.return_value = {"results": []}
        repos = self.finder._query_paperswithcode("Nonexistent Paper Title")
        self.assertEqual(repos, [])

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_api_returns_none(self, mock_http):
        """Should return empty list when API fails."""
        mock_http.return_value = None
        repos = self.finder._query_paperswithcode("Some Paper")
        self.assertEqual(repos, [])


class TestImplFinderGitHub(unittest.TestCase):
    """Test GitHub Search query method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_successful_query(self, mock_http):
        """Should return repos from GitHub search."""
        mock_http.return_value = {
            "items": [
                {
                    "full_name": "org/repo1",
                    "html_url": "https://github.com/org/repo1",
                    "stargazers_count": 5000,
                    "language": "Python",
                    "description": "A great repo",
                    "pushed_at": "2025-06-01T00:00:00Z",
                }
            ]
        }

        repos = self.finder._query_github(["deep", "learning"], min_stars=50)
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "org/repo1")
        self.assertEqual(repos[0]["stars"], 5000)
        self.assertEqual(repos[0]["source"], "github")

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_empty_results(self, mock_http):
        """Should return empty list when no repos found."""
        mock_http.return_value = {"items": []}
        repos = self.finder._query_github(["nonexistent"])
        self.assertEqual(repos, [])

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_api_failure(self, mock_http):
        """Should return empty list when API fails."""
        mock_http.return_value = None
        repos = self.finder._query_github(["test"])
        self.assertEqual(repos, [])


class TestImplFinderHuggingFace(unittest.TestCase):
    """Test Hugging Face query method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_returns_models_and_datasets(self, mock_http):
        """Should return both models and datasets."""
        mock_http.side_effect = [
            # Models response
            [{"id": "bert-base-uncased", "downloads": 50000000, "pipeline_tag": "fill-mask"}],
            # Datasets response
            [{"id": "squad", "downloads": 10000000}],
        ]

        results = self.finder._query_huggingface(["bert", "nlp"])
        self.assertTrue(len(results) >= 1)
        sources = [r["source"] for r in results]
        self.assertTrue(all(s == "huggingface" for s in sources))
        types = [r["type"] for r in results]
        self.assertIn("model", types)
        self.assertIn("dataset", types)

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_api_failure_graceful(self, mock_http):
        """Should return empty list when API fails."""
        mock_http.return_value = None
        results = self.finder._query_huggingface(["test"])
        self.assertEqual(results, [])


class TestImplFinderPyPI(unittest.TestCase):
    """Test PyPI query method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_successful_lookup(self, mock_http):
        """Should return package info for known packages."""
        mock_http.return_value = {
            "info": {
                "name": "scikit-learn",
                "version": "1.5.0",
                "summary": "Machine learning library",
                "project_url": "https://pypi.org/project/scikit-learn/",
                "home_page": "https://scikit-learn.org",
            }
        }

        packages = self.finder._query_pypi(["machine", "learning"])
        self.assertTrue(len(packages) >= 1)
        self.assertEqual(packages[0]["name"], "scikit-learn")
        self.assertEqual(packages[0]["source"], "pypi")

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_package_not_found(self, mock_http):
        """Should skip packages that don't exist."""
        mock_http.return_value = None
        packages = self.finder._query_pypi(["zzz_nonexistent_pkg"])
        self.assertEqual(packages, [])


class TestImplFinderClinicalTrials(unittest.TestCase):
    """Test ClinicalTrials.gov query method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_successful_query(self, mock_http):
        """Should return trial info."""
        mock_http.return_value = {
            "studies": [{
                "protocolSection": {
                    "identificationModule": {
                        "nctId": "NCT12345678",
                        "briefTitle": "Phase 3 Study of Drug X"
                    },
                    "statusModule": {"overallStatus": "RECRUITING"},
                    "designModule": {"phases": ["PHASE3"]}
                }
            }]
        }

        trials = self.finder._query_clinicaltrials(["drug", "cancer"])
        self.assertEqual(len(trials), 1)
        self.assertEqual(trials[0]["nct_id"], "NCT12345678")
        self.assertEqual(trials[0]["status"], "RECRUITING")
        self.assertEqual(trials[0]["source"], "clinicaltrials")

    @patch.object(ImplementationFinder, '_http_get_json')
    def test_api_failure(self, mock_http):
        """Should return empty list when API fails."""
        mock_http.return_value = None
        trials = self.finder._query_clinicaltrials(["test"])
        self.assertEqual(trials, [])


class TestImplFinderFind(unittest.TestCase):
    """Test the main find() orchestration method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    @patch.object(ImplementationFinder, '_query_paperswithcode')
    @patch.object(ImplementationFinder, '_query_github')
    @patch.object(ImplementationFinder, '_query_awesome_lists')
    @patch.object(ImplementationFinder, '_query_huggingface')
    @patch.object(ImplementationFinder, '_query_pypi')
    def test_returns_all_result_keys(self, mock_pypi, mock_hf, mock_awesome, mock_gh, mock_pwc):
        """find() should return all expected result keys."""
        mock_pwc.return_value = []
        mock_gh.return_value = []
        mock_awesome.return_value = []
        mock_hf.return_value = []
        mock_pypi.return_value = []

        result = self.finder.find({
            "idea_title": "Test Idea",
            "field": "cs.AI",
            "inspiration_title": "Some Paper",
            "methodology_hint": "deep learning",
        })

        expected_keys = {"paper_repos", "related_repos", "awesome_lists",
                         "models_datasets", "packages", "clinical_trials",
                         "compounds", "proteins", "datasets", "meta"}
        self.assertEqual(set(result.keys()), expected_keys)

    @patch.object(ImplementationFinder, '_query_paperswithcode')
    @patch.object(ImplementationFinder, '_query_github')
    @patch.object(ImplementationFinder, '_query_awesome_lists')
    @patch.object(ImplementationFinder, '_query_huggingface')
    @patch.object(ImplementationFinder, '_query_pypi')
    def test_meta_tracks_sources(self, mock_pypi, mock_hf, mock_awesome, mock_gh, mock_pwc):
        """meta.sources_queried should list all sources that were called."""
        mock_pwc.return_value = [{"name": "repo", "url": "http://x", "stars": 1, "framework": "", "description": "", "source": "paperswithcode"}]
        mock_gh.return_value = []
        mock_awesome.return_value = []
        mock_hf.return_value = []
        mock_pypi.return_value = []

        result = self.finder.find({
            "idea_title": "Test",
            "field": "cs.AI",
            "inspiration_title": "Paper Title",
            "methodology_hint": "transformers",
        })

        self.assertIn("paperswithcode", result["meta"]["sources_queried"])
        self.assertIn("github", result["meta"]["sources_queried"])
        self.assertIn("duration_ms", result["meta"])

    @patch.object(ImplementationFinder, '_query_paperswithcode')
    @patch.object(ImplementationFinder, '_query_github')
    @patch.object(ImplementationFinder, '_query_awesome_lists')
    @patch.object(ImplementationFinder, '_query_huggingface')
    @patch.object(ImplementationFinder, '_query_pypi')
    def test_graceful_failure(self, mock_pypi, mock_hf, mock_awesome, mock_gh, mock_pwc):
        """If one source throws, others should still return results."""
        mock_pwc.side_effect = Exception("API down")
        mock_gh.return_value = [{"name": "org/repo", "url": "http://x", "stars": 100, "lang": "Python", "description": "", "pushed_at": "", "source": "github"}]
        mock_awesome.return_value = []
        mock_hf.return_value = []
        mock_pypi.return_value = []

        result = self.finder.find({
            "idea_title": "Test",
            "field": "cs.AI",
            "inspiration_title": "Paper",
            "methodology_hint": "deep learning",
        })

        # PwC failed but GitHub succeeded
        self.assertEqual(result["paper_repos"], [])
        self.assertEqual(len(result["related_repos"]), 1)
        self.assertNotIn("paperswithcode", result["meta"]["sources_queried"])
        self.assertIn("github", result["meta"]["sources_queried"])

    def test_no_inspiration_skips_pwc(self):
        """If no inspiration_title, Papers With Code should be skipped."""
        with patch.object(self.finder, '_query_paperswithcode') as mock_pwc:
            with patch.object(self.finder, '_query_github', return_value=[]):
                with patch.object(self.finder, '_query_awesome_lists', return_value=[]):
                    with patch.object(self.finder, '_query_huggingface', return_value=[]):
                        with patch.object(self.finder, '_query_pypi', return_value=[]):
                            self.finder.find({"idea_title": "Test", "field": "cs.AI"})
            mock_pwc.assert_not_called()


class TestImplFinderKaggle(unittest.TestCase):
    """Test Kaggle query method."""

    def setUp(self):
        self.finder = ImplementationFinder()

    def test_no_credentials_returns_empty(self):
        """Should return empty list when Kaggle credentials not set."""
        with patch.dict('os.environ', {}, clear=True):
            results = self.finder._query_kaggle(["test"])
        self.assertEqual(results, [])

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'KAGGLE_USERNAME': 'user', 'KAGGLE_KEY': 'key123'})
    def test_successful_query(self, mock_urlopen):
        """Should return datasets when credentials are set."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            {"ref": "user/dataset1", "title": "Test Dataset", "subtitle": "A test", "downloadCount": 5000, "usabilityRating": 0.8}
        ]).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock()
        mock_urlopen.return_value = mock_response

        results = self.finder._query_kaggle(["machine", "learning"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Dataset")
        self.assertEqual(results[0]["source"], "kaggle")


class TestImplFinderConfigCredentials(unittest.TestCase):
    """Optional integration credentials can come from config.yaml too."""

    def test_github_token_falls_back_to_config(self):
        old = Config.GITHUB_TOKEN
        try:
            Config.GITHUB_TOKEN = "cfg-token"
            finder = ImplementationFinder()
            self.assertEqual(finder._github_token, "cfg-token")
        finally:
            Config.GITHUB_TOKEN = old

    @patch("urllib.request.urlopen")
    @patch.dict("os.environ", {}, clear=True)
    def test_kaggle_query_uses_config_credentials(self, mock_urlopen):
        old_user = Config.KAGGLE_USERNAME
        old_key = Config.KAGGLE_KEY
        try:
            Config.KAGGLE_USERNAME = "cfg-user"
            Config.KAGGLE_KEY = "cfg-key"
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps([]).encode()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock()
            mock_urlopen.return_value = mock_response

            finder = ImplementationFinder()
            finder._query_kaggle(["vision"])

            request_obj = mock_urlopen.call_args.args[0]
            self.assertEqual(request_obj.headers.get("Authorization"), "Basic Y2ZnLXVzZXI6Y2ZnLWtleQ==")
        finally:
            Config.KAGGLE_USERNAME = old_user
            Config.KAGGLE_KEY = old_key


if __name__ == '__main__':
    unittest.main()
