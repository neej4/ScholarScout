from abc import ABC, abstractmethod
from typing import List
from src.core.models import Paper

class BaseFetcher(ABC):
    """
    Kelas dasar untuk semua Paper Fetcher (arXiv, Scopus, dll).
    Setiap fetcher baru harus mewarisi kelas ini dan mengimplementasikan fetch_papers.
    """
    
    @abstractmethod
    def fetch_papers(self, category: str, max_results: int = 50) -> List[Paper]:
        """
        Mengambil paper berdasarkan kategori.
        
        Args:
            category (str): Kategori penelitian.
            max_results (int): Maksimal paper yang diambil.
            
        Returns:
            List[Paper]: Daftar objek paper hasil scraping.
        """
        pass
