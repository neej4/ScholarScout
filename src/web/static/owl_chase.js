/**
 * Owl Chase — Interactive pipeline visualization game
 * Owl catches paper dots while pipeline runs. Driven by real SSE events.
 * 
 * Usage:
 *   const game = new OwlChase('gameCanvas');
 *   game.start();
 *   game.onPaperFound('arXiv', 'Paper title...');  // called by SSE handler
 *   game.onPhaseChange('analyze');
 *   game.stop();
 */

const SOURCE_COLORS = {
  'arxiv': '#ffffff',
  'openalex': '#aaaaaa',
  'semantic_scholar': '#6699ff',
  'pubmed': '#66cc66',
  'crossref': '#cc66cc',
  'doaj': '#88cc88',
  'scopus': '#ffaa44',
  'dblp': '#ffaa44',
  'cache': '#555555',
};

class OwlChase {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.ctx.imageSmoothingEnabled = false;
    this.ctx.mozImageSmoothingEnabled = false;
    this.ctx.webkitImageSmoothingEnabled = false;

    this.W = this.canvas.width;
    this.H = this.canvas.height;
    this.GROUND = this.H - 44;
    this.GRAVITY = 0.7;
    this.JUMP_FORCE = -11;

    this.owl = {x:50, y:this.GROUND, vy:0, jumping:false, anim:'idle', frame:0, frameTimer:0, scale:2};
    this.papers = [];
    this.effects = [];
    this.score = 0;
    this.total = 0;
    this.scrollOffset = 0;
    this.running = false;
    this.lastTime = 0;
    this.animId = null;

    // Sprite
    this.sprite = new Image();
    this.sprite.src = '/static/owl_sprite.png';
    this.ANIMS = {
      idle:  {start:0, end:3, speed:200},
      walk:  {start:4, end:7, speed:120},
      jump:  {start:8, end:11, speed:100},
    };

    // Input
    this._bindInput();
  }

  _bindInput() {
    const jump = () => {
      if (!this.owl.jumping && this.running) {
        this.owl.jumping = true;
        this.owl.vy = this.JUMP_FORCE;
        this.owl.anim = 'jump';
        this.owl.frame = this.ANIMS.jump.start;
      }
    };
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && this._isVisible()) { e.preventDefault(); jump(); }
    });
    this.canvas.addEventListener('mousedown', (e) => { e.preventDefault(); jump(); });
    this.canvas.addEventListener('touchstart', (e) => { e.preventDefault(); jump(); });
  }

  _isVisible() {
    return this.canvas.offsetParent !== null;
  }

  start() {
    this.running = true;
    this.score = 0;
    this.total = 0;
    this.papers = [];
    this.effects = [];
    this.scrollOffset = 0;
    this.owl.y = this.GROUND;
    this.owl.vy = 0;
    this.owl.jumping = false;
    this.owl.anim = 'walk';
    this.owl.frame = this.ANIMS.walk.start;
    this.lastTime = performance.now();
    this._loop(this.lastTime);
  }

  stop() {
    this.running = false;
    this.owl.anim = 'idle';
    if (this.animId) cancelAnimationFrame(this.animId);
  }

  getScore() { return {caught: this.score, total: this.total}; }

  // Called by SSE handler when a paper is fetched
  onPaperFound(source, title) {
    if (!this.running) return;
    const lanes = [this.GROUND+10, this.GROUND-35, this.GROUND-75];
    const lane = lanes[Math.floor(Math.random()*3)];
    const color = SOURCE_COLORS[source] || '#ffffff';
    this.papers.push({
      x: this.W + 10, y: lane,
      speed: 2.5 + Math.random()*1.5,
      color: color, source: source,
      caught: false
    });
    this.total++;
  }

  // Called when pipeline phase changes
  onPhaseChange(phase) {
    if (phase === 'done') {
      this.owl.anim = 'idle';
    }
  }

  _loop(timestamp) {
    if (!this.running) return;
    const dt = timestamp - this.lastTime;
    this.lastTime = timestamp;

    this._update(dt);
    this._draw();
    this.animId = requestAnimationFrame((t) => this._loop(t));
  }

  _update(dt) {
    // Parallax
    this.scrollOffset += 0.5;

    // Owl physics
    if (this.owl.jumping) {
      this.owl.vy += this.GRAVITY;
      this.owl.y += this.owl.vy;
      if (this.owl.y >= this.GROUND) {
        this.owl.y = this.GROUND;
        this.owl.vy = 0;
        this.owl.jumping = false;
        this.owl.anim = 'walk';
        this.owl.frame = this.ANIMS.walk.start;
      }
    }

    // Animate sprite
    this.owl.frameTimer += dt;
    const anim = this.ANIMS[this.owl.anim];
    if (this.owl.frameTimer >= anim.speed) {
      this.owl.frameTimer = 0;
      this.owl.frame++;
      if (this.owl.frame > anim.end) this.owl.frame = anim.start;
    }

    // Papers
    for (let i = this.papers.length-1; i >= 0; i--) {
      let p = this.papers[i];
      if (p.caught) continue;
      p.x -= p.speed;
      // Collision
      const dist = Math.sqrt((this.owl.x+32-p.x)**2 + (this.owl.y+16-p.y)**2);
      if (dist < 30) {
        p.caught = true;
        this.score++;
        this.effects.push({x:p.x, y:p.y, color:p.color, life:1});
      }
      if (p.x < -20) this.papers.splice(i, 1);
    }

    // Effects
    this.effects = this.effects.filter(e => { e.life -= 0.04; return e.life > 0; });
  }

  _draw() {
    const ctx = this.ctx;
    const W = this.W, H = this.H;
    ctx.clearRect(0, 0, W, H);

    const groundY = this.GROUND + 32*this.owl.scale/2 + 4;

    // Parallax forest
    // Layer 1: far hills
    ctx.fillStyle = '#1a1a1a';
    for (let i = 0; i < 12; i++) {
      const bx = ((i*80) - (this.scrollOffset*0.2) % 960 + 960) % 960 - 40;
      const bh = 20 + (i%4)*8;
      ctx.fillRect(Math.round(bx), groundY-bh, 16, bh);
      ctx.fillRect(Math.round(bx)-4, groundY-bh+4, 24, bh-4);
    }
    // Layer 2: mid trees
    ctx.fillStyle = '#222';
    for (let i = 0; i < 8; i++) {
      const tx = ((i*110+30) - (this.scrollOffset*0.5) % 880 + 880) % 880 - 20;
      const x = Math.round(tx);
      ctx.fillRect(x-2, groundY-6, 4, 6);
      ctx.fillRect(x-6, groundY-35-(i%3)*10, 12, 8);
      ctx.fillRect(x-8, groundY-35-(i%3)*10+8, 16, 8);
      ctx.fillRect(x-10, groundY-35-(i%3)*10+16, 20, 35+(i%3)*10-22);
    }
    // Layer 3: near bushes
    ctx.fillStyle = '#2a2a2a';
    for (let i = 0; i < 6; i++) {
      const tx = ((i*150+60) - (this.scrollOffset*1.0) % 900 + 900) % 900 - 30;
      const x = Math.round(tx);
      ctx.fillRect(x, groundY-12, 8, 12);
      ctx.fillRect(x-4, groundY-8, 16, 8);
    }

    // Ground
    ctx.fillStyle = '#333';
    ctx.fillRect(0, groundY, W, 2);
    ctx.fillStyle = '#252525';
    for (let i = 0; i < 20; i++) {
      const gx = ((i*23+5) - (this.scrollOffset*1.2) % 460 + 460) % 460;
      ctx.fillRect(Math.round(gx), groundY+4, 2, 2);
    }

    // Papers (4x4 squares)
    for (let p of this.papers) {
      if (p.caught) continue;
      ctx.fillStyle = p.color;
      ctx.fillRect(Math.round(p.x)-2, Math.round(p.y)-2, 4, 4);
    }

    // Effects (expanding pixel square)
    for (let e of this.effects) {
      ctx.globalAlpha = e.life;
      ctx.strokeStyle = e.color;
      ctx.lineWidth = 1;
      const size = Math.round(8*(1-e.life)+4);
      ctx.strokeRect(Math.round(e.x)-size/2, Math.round(e.y)-size/2, size, size);
      ctx.globalAlpha = 1;
    }

    // Owl sprite
    if (this.sprite.complete && this.sprite.naturalWidth > 0) {
      const sx = this.owl.frame * 32;
      const size = 32 * this.owl.scale;
      ctx.drawImage(this.sprite, sx, 0, 32, 32, this.owl.x, this.owl.y - size/2 + 16, size, size);
    }

    // Score
    ctx.fillStyle = '#555';
    ctx.font = '9px monospace';
    ctx.fillText(`${this.score}/${this.total}`, W-45, 14);
  }
}
