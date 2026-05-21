# JavaScript Tests for ScholarScout

This directory contains JavaScript unit and property-based tests for the ScholarScout web components.

## Setup

The test infrastructure uses:
- **Jest**: JavaScript testing framework
- **fast-check**: Property-based testing library
- **jsdom**: DOM implementation for Node.js (for testing browser code)

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch
```

## Test Files

- `bookmarks.test.js` - Unit tests for bookmark functionality

## Bookmark Module

The bookmark functions have been extracted from `dashboard.html` into a separate module at `src/web/static/bookmarks.js` to enable testing. The module includes:

- `getBookmarks()` - Retrieve all bookmarked ideas
- `saveBookmarks(arr)` - Save bookmarks to localStorage
- `isBookmarked(title)` - Check if an idea is bookmarked
- `addBookmark(idea)` - Add an idea to bookmarks
- `removeBookmark(title)` - Remove an idea from bookmarks
- `isLocalStorageAvailable()` - Check if localStorage is available

## Property-Based Tests

Property-based tests will be added in task 12.2 using fast-check to verify:
- Bookmark round-trip property (save and retrieve)
- Bookmark toggle idempotence (add then remove returns to original state)
