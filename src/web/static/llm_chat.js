/**
 * LLM Chat Panel — Narrated conversation between Scout and LLM.
 * Translates SSE pipeline events into casual human-readable chat bubbles.
 * No hardcoded messages — all driven by event data.
 */

class LLMChatPanel {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.messages = [];
  }

  clear() {
    this.messages = [];
    if (this.container) this.container.innerHTML = '';
  }

  /**
   * Process an SSE event and append a chat bubble if relevant.
   * @param {object} data — parsed SSE event object
   */
  handleEvent(data) {
    const ev = data.event;
    const bubble = this._eventToBubble(ev, data);
    if (bubble) {
      this._append(bubble.from, bubble.text);
    }
  }

  /**
   * Map SSE event to a chat bubble. Returns null if event is not chat-worthy.
   */
  _eventToBubble(ev, data) {
    switch (ev) {
      case 'start':
        return {
          from: 'scout',
          text: `Starting up. Model: ${data.model || 'unknown'}. Let's find some papers.`
        };

      case 'phase':
        if (data.phase === 0) return {from: 'scout', text: 'Checking if the AI is reachable...'};
        if (data.phase === 1) return {from: 'scout', text: `Scanning databases for papers...`};
        if (data.phase === 2) return {from: 'scout', text: data.msg || 'Analyzing what I found...'};
        if (data.phase === 3) return {from: 'scout', text: data.msg || 'Working on the next step...'};
        if (data.phase === 4) return {from: 'scout', text: data.msg || 'Almost there...'};
        if (data.phase === 5) return {from: 'scout', text: data.msg || 'Wrapping up...'};
        return null;

      case 'ping_ok':
        return {from: 'llm', text: 'Connected. Ready to go.'};

      case 'phase1_done':
        return {
          from: 'scout',
          text: `Got ${data.total || 0} papers total. That should be enough to work with.`
        };

      case 'cat_done':
        if (data.count && data.cat) {
          return {from: 'llm', text: `Found ${data.count} papers for ${data.cat}.`};
        }
        return null;

      case 'cat_skip':
        if (data.cat) {
          return {from: 'scout', text: `Using cached papers for ${data.cat} — already have enough.`};
        }
        return null;

      case 'trend':
        if (data.keywords && data.cat) {
          const kw = Array.isArray(data.keywords) ? data.keywords.join(', ') : data.keywords;
          const conf = data.confidence ? ` (confidence: ${data.confidence}/10)` : '';
          return {
            from: 'llm',
            text: `${data.cat}: trending topics are ${kw}${conf}.`
          };
        }
        return null;

      case 'phase2_done':
        return {from: 'scout', text: 'Trend analysis done. Now I know where the gaps are.'};

      case 'gen_start':
        if (data.cat) {
          return {from: 'scout', text: data.msg || `Working on ${data.cat}...`};
        }
        return null;

      case 'cat_ideas':
        if (data.count && data.cat) {
          return {from: 'llm', text: data.msg || `Done with ${data.cat}. Total so far: ${data.total || '?'}.`};
        }
        return null;

      case 'phase3_done':
        return {from: 'llm', text: data.msg || 'All done with this phase.'};

      case 'cluster_form':
        if (data.cluster_name) {
          return {from: 'llm', text: `Found a theme: "${data.cluster_name}" (${data.count || '?'} papers).`};
        }
        return null;

      case 'done':
        return {
          from: 'scout',
          text: data.msg || 'Done! Check the results.'
        };

      case 'fatal_error':
        return {from: 'scout', text: `Something went wrong: ${data.msg || 'unknown error'}. Check Settings.`};

      case 'llm_wait':
        return {from: 'llm', text: data.msg || 'Rate limited, waiting a moment...'};

      case 'llm_error':
        return {from: 'llm', text: `Error: ${(data.msg || '').slice(0, 100)}`};

      case 'cache_expiry':
        return {from: 'scout', text: data.msg || 'Cleaned up old cached papers.'};

      case 'dedup':
        return {from: 'scout', text: data.msg || 'Loaded previous titles to avoid duplicates.'};

      default:
        return null;
    }
  }

  _append(from, text) {
    if (!this.container) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble chat-${from}`;
    bubble.innerHTML = `<span class="chat-name">${from === 'scout' ? 'Scout' : 'AI'}</span><span class="chat-text">${this._escapeHtml(text)}</span>`;
    this.container.appendChild(bubble);
    this.container.scrollTop = this.container.scrollHeight;
    this.messages.push({from, text});
  }

  _escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }
}
