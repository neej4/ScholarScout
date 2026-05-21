/**
 * Bookmark management module for ScholarScout
 * Handles localStorage operations for bookmarking research ideas
 */

// Check localStorage availability
let localStorageAvailable = false;
(function checkLocalStorage() {
  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    localStorageAvailable = true;
  } catch(e) {
    localStorageAvailable = false;
  }
})();

/**
 * Retrieve all bookmarked ideas from localStorage
 * @returns {Array<Object>} Array of bookmarked idea objects
 */
function getBookmarks() {
  if (!localStorageAvailable) return [];
  try {
    return JSON.parse(localStorage.getItem('scholarscout_bookmarks') || '[]');
  } catch (e) {
    console.error('Failed to parse bookmarks:', e);
    return [];
  }
}

/**
 * Save bookmarks array to localStorage
 * @param {Array<Object>} arr - Array of idea objects to save
 */
function saveBookmarks(arr) {
  if (!localStorageAvailable) return;
  try {
    localStorage.setItem('scholarscout_bookmarks', JSON.stringify(arr));
  } catch (e) {
    console.error('Failed to save bookmarks:', e);
  }
}

/**
 * Check if an idea is bookmarked
 * @param {string} title - The idea_title to check
 * @returns {boolean} True if the idea is bookmarked
 */
function isBookmarked(title) {
  return getBookmarks().some(idea => idea.idea_title === title);
}

/**
 * Add an idea to bookmarks
 * @param {Object} idea - The full idea object to bookmark
 */
function addBookmark(idea) {
  let bm = getBookmarks();
  // Skip duplicate based on idea_title
  if (bm.some(b => b.idea_title === idea.idea_title)) {
    return;
  }
  bm.push(idea);
  saveBookmarks(bm);
}

/**
 * Remove an idea from bookmarks by title
 * @param {string} title - The idea_title to remove
 */
function removeBookmark(title) {
  let bm = getBookmarks();
  bm = bm.filter(idea => idea.idea_title !== title);
  saveBookmarks(bm);
}

/**
 * Check if localStorage is available
 * @returns {boolean} True if localStorage is available
 */
function isLocalStorageAvailable() {
  return localStorageAvailable;
}

// Export for Node.js/Jest environment
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getBookmarks,
    saveBookmarks,
    isBookmarked,
    addBookmark,
    removeBookmark,
    isLocalStorageAvailable
  };
}
