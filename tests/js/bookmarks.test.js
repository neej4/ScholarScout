/**
 * Unit tests for bookmark functionality
 * Tests the core bookmark management functions
 */

// Mock localStorage for testing
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => { store[key] = value.toString(); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

global.localStorage = localStorageMock;

// Import the bookmark functions
const {
  getBookmarks,
  saveBookmarks,
  isBookmarked,
  addBookmark,
  removeBookmark,
  isLocalStorageAvailable
} = require('../../src/web/static/bookmarks.js');

describe('Bookmark Functions', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  describe('getBookmarks', () => {
    test('should return empty array when no bookmarks exist', () => {
      const bookmarks = getBookmarks();
      expect(bookmarks).toEqual([]);
    });

    test('should return array of bookmarked ideas', () => {
      const testIdeas = [
        { idea_title: 'Test Idea 1', abstract: 'Abstract 1' },
        { idea_title: 'Test Idea 2', abstract: 'Abstract 2' }
      ];
      localStorage.setItem('scholarscout_bookmarks', JSON.stringify(testIdeas));
      
      const bookmarks = getBookmarks();
      expect(bookmarks).toEqual(testIdeas);
    });

    test('should return empty array on parse error', () => {
      localStorage.setItem('scholarscout_bookmarks', 'invalid json');
      const bookmarks = getBookmarks();
      expect(bookmarks).toEqual([]);
    });
  });

  describe('saveBookmarks', () => {
    test('should save bookmarks to localStorage', () => {
      const testIdeas = [
        { idea_title: 'Test Idea 1', abstract: 'Abstract 1' }
      ];
      saveBookmarks(testIdeas);
      
      const stored = JSON.parse(localStorage.getItem('scholarscout_bookmarks'));
      expect(stored).toEqual(testIdeas);
    });
  });

  describe('isBookmarked', () => {
    test('should return false when idea is not bookmarked', () => {
      expect(isBookmarked('Non-existent Idea')).toBe(false);
    });

    test('should return true when idea is bookmarked', () => {
      const testIdea = { idea_title: 'Test Idea', abstract: 'Abstract' };
      addBookmark(testIdea);
      
      expect(isBookmarked('Test Idea')).toBe(true);
    });
  });

  describe('addBookmark', () => {
    test('should add idea to bookmarks', () => {
      const testIdea = { idea_title: 'Test Idea', abstract: 'Abstract' };
      addBookmark(testIdea);
      
      const bookmarks = getBookmarks();
      expect(bookmarks).toHaveLength(1);
      expect(bookmarks[0]).toEqual(testIdea);
    });

    test('should not add duplicate ideas', () => {
      const testIdea = { idea_title: 'Test Idea', abstract: 'Abstract' };
      addBookmark(testIdea);
      addBookmark(testIdea);
      
      const bookmarks = getBookmarks();
      expect(bookmarks).toHaveLength(1);
    });

    test('should add multiple different ideas', () => {
      const idea1 = { idea_title: 'Idea 1', abstract: 'Abstract 1' };
      const idea2 = { idea_title: 'Idea 2', abstract: 'Abstract 2' };
      
      addBookmark(idea1);
      addBookmark(idea2);
      
      const bookmarks = getBookmarks();
      expect(bookmarks).toHaveLength(2);
    });
  });

  describe('removeBookmark', () => {
    test('should remove idea from bookmarks', () => {
      const testIdea = { idea_title: 'Test Idea', abstract: 'Abstract' };
      addBookmark(testIdea);
      
      removeBookmark('Test Idea');
      
      const bookmarks = getBookmarks();
      expect(bookmarks).toHaveLength(0);
    });

    test('should only remove specified idea', () => {
      const idea1 = { idea_title: 'Idea 1', abstract: 'Abstract 1' };
      const idea2 = { idea_title: 'Idea 2', abstract: 'Abstract 2' };
      
      addBookmark(idea1);
      addBookmark(idea2);
      removeBookmark('Idea 1');
      
      const bookmarks = getBookmarks();
      expect(bookmarks).toHaveLength(1);
      expect(bookmarks[0].idea_title).toBe('Idea 2');
    });
  });

  describe('isLocalStorageAvailable', () => {
    test('should return true when localStorage is available', () => {
      expect(isLocalStorageAvailable()).toBe(true);
    });
  });
});
