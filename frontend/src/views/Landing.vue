<template>
  <div class="landing-page" :class="themeClass">
    <!-- 粒子背景 Canvas -->
    <canvas ref="particleCanvas" class="particle-canvas"></canvas>
    <div class="bg-glow bg-glow--one"></div>
    <div class="bg-glow bg-glow--two"></div>
    <div class="bg-grid"></div>

    <header class="topbar">
      <router-link class="brand" to="/"><span class="brand-mark">📄</span> DocuLogic</router-link>
      <div class="topbar-actions">
        <template v-if="user">
          <router-link class="btn btn-ghost" to="/app">工作台</router-link>
        </template>
        <template v-else>
          <router-link class="btn btn-ghost" to="/login">登录</router-link>
          <router-link v-if="registrationEnabled" class="btn btn-primary" to="/register">注册</router-link>
        </template>
      </div>
    </header>
    <section class="hero">
      <div class="hero-badge">
        <span class="badge-dot"></span>
        <span>Production Ready · Plugin Driven</span>
      </div>
      <h1 class="hero-title">
        <span class="title-text" data-text="DocuLogic 文档解析平台">DocuLogic 文档解析平台</span>
      </h1>
      <p>
        面向 <strong>PDF / 图片</strong> 的结构化解析工作台：基于 <strong>Logics-Parsing-v2</strong> 与 <strong>PaddleOCR-3.5</strong>
        插件化引擎，将扫描件、截图与文档页转换为规范 Markdown，覆盖文本、表格、公式、流程图、化学式、乐谱、伪代码等复杂内容。
        支持后台模型管理、实时进度、任务中断、历史记录与批量下载，适合知识库构建与企业文档自动化。
      </p>
      <div class="hero-cta">
        <template v-if="user">
          <router-link class="btn btn-primary" to="/app">进入工作台</router-link>
        </template>
        <template v-else>
          <router-link v-if="registrationEnabled" class="btn btn-primary" to="/register">免费注册</router-link>
          <router-link class="btn btn-ghost" to="/login">已有账号登录</router-link>
        </template>
      </div>
      <div class="hero-stats">
        <div class="hero-stat">
          <strong>2</strong>
          <span>内置转换器</span>
        </div>
        <div class="hero-stat">
          <strong>3</strong>
          <span>图片输出模式</span>
        </div>
        <div class="hero-stat">
          <strong>实时</strong>
          <span>WebSocket 进度追踪</span>
        </div>
      </div>
    </section>

    <section class="landing-block reveal-on-scroll">
      <h2 class="landing-title">核心特色</h2>
      <p class="landing-sub">围绕当前已落地能力设计：可部署、可观测、可维护。</p>
      <div class="features">
        <div class="feature">
          <div class="feature-icon icon-brain">🧠</div>
          <h3>双转换器插件化引擎</h3>
          <p>Logics-Parsing-v2 与 PaddleOCR-3.5 可切换，下载/状态/清理统一接口</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-crop">✂️</div>
          <h3>复杂文档结构识别</h3>
          <p>文本、表格、公式、流程图、化学式、乐谱、伪代码等内容统一输出</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-palette">🎨</div>
          <h3>可配置输出策略</h3>
          <p>支持 Base64 / 独立文件 / 不输出 三种图片模式，兼顾效果与体积</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-package">📦</div>
          <h3>部署前置检查</h3>
          <p>本地与 Docker 启动前检查 converts/models 是否已准备，避免运行时缺依赖</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-bolt">⚡</div>
          <h3>实时进度与任务管理</h3>
          <p>WebSocket 状态追踪、任务停止、历史记录、批量下载与缓存清理</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-shield">🔐</div>
          <h3>后台模型运维闭环</h3>
          <p>支持模型下载、停止、清理、重载、卸载与路径配置，减少手工维护成本</p>
        </div>
      </div>
    </section>

    <section class="landing-block reveal-on-scroll">
      <h2 class="landing-title">技术架构</h2>
      <p class="landing-sub">前后端分离 + 插件化转换器 + Docker 部署，关注可扩展与稳定性。</p>
      <div class="features">
        <div class="feature">
          <div class="feature-icon icon-rocket">🚀</div>
          <h3>FastAPI 中间件调度</h3>
          <p>统一转换器协议，解析链路通过 host/registry 插件分发，便于新增引擎</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-globe">🌐</div>
          <h3>FastAPI + Vue 3</h3>
          <p>前后端分离，REST API + WebSocket 双通道通信</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-database">🗄️</div>
          <h3>MySQL/SQLite等多种数据库灵活切换</h3>
          <p>无缝切换数据库，Docker Compose 一键部署</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-lock">🔒</div>
          <h3>多层安全防护</h3>
          <p>JWT、bcrypt、验证码、速率限制、SQL 注入防护</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-settings">⚙️</div>
          <h3>灵活配置管理</h3>
          <p>环境变量 + 管理后台双重配置，下载路径与模型加载路径保持一致</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-chart">📊</div>
          <h3>完善的日志与监控</h3>
          <p>下载过程、重载失败、会话校验等关键节点均有可追踪日志</p>
        </div>
      </div>
    </section>

    <section class="landing-block reveal-on-scroll">
      <h2 class="landing-title">部署与模型准备</h2>
      <p class="landing-sub">与当前项目实现保持一致的上线流程。</p>
      <div class="features">
        <div class="feature">
          <div class="feature-icon icon-book">📚</div>
          <h3>步骤 1：准备源码目录</h3>
          <p>部署前需准备本地 converts/models（目录存在且非空），该目录不提交到 GitHub</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-briefcase">💼</div>
          <h3>步骤 2：启动服务</h3>
          <p>支持本地启动或 Docker 部署，系统会在启动前自动检查 models 目录状态</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-graduation">🎓</div>
          <h3>步骤 3：后台下载权重</h3>
          <p>进入工作台后在「模型配置」执行下载，权重统一写入 weights/转换器目录</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-archive">🏛️</div>
          <h3>步骤 4：加载并校验</h3>
          <p>下载完成后可在后台重载/卸载模型，并查看状态提示与错误反馈</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-flask">🔬</div>
          <h3>支持输入</h3>
          <p>当前仅支持 PDF 与图片格式，不包含音频/视频解析链路</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-newspaper">📰</div>
          <h3>支持输出</h3>
          <p>Markdown、原始输出、可视化标注图与资源包下载，便于二次处理与集成</p>
        </div>
      </div>
    </section>

    <section class="landing-block landing-block--narrow reveal-on-scroll">
      <h2 class="landing-title">支持的文档类型</h2>
      <div class="landing-detail">
        <p>
          <strong>图像格式：</strong>PNG、JPG/JPEG、WebP、BMP、TIFF 等常见图片格式，支持扫描件、截图、照片等多种来源。
        </p>
        <p>
          <strong>PDF 文档：</strong>支持单页或多页 PDF，自动分页渲染为 PNG 后逐页处理；管理员可配置最大页数限制（默认 80 页），防止资源滥用。
        </p>
        <p>
          <strong>复杂版面：</strong>能够处理图文混排、多栏布局、表格嵌套、LaTeX 公式、Mermaid 流程图、ABC 记谱法、化学式（SMILES）、伪代码块等复杂结构，保持原文档的逻辑层次。
        </p>
        <p>
          <strong>专业支持：</strong>特别优化对数学公式、化学分子式、物理图表、生物图谱、乐谱、手写文本等专业领域内容的识别与转换。
        </p>
      </div>
    </section>

    <section class="landing-block landing-block--narrow reveal-on-scroll">
      <h2 class="landing-title">输出与对接</h2>
      <div class="landing-detail">
        <p>
          <strong>📄 完整输出包：</strong>规范 Markdown（.md）、原始模型输出、可视化标注图（带 bbox）及独立图像文件。
        </p>
        <p>
          <strong>🖼️ 三种图像模式：</strong>Base64 嵌入（单文件）、独立文件（ZIP 打包）、不输出（纯文本），灵活配置。
        </p>
        <p>
          <strong>⚡ RESTful API + WebSocket：</strong>支持上传、查询、下载、停止等操作，实时推送解析进度，轻松集成企业系统。
        </p>
        <p>
          <strong>🚀 灵活部署：</strong>Docker 一键部署（5分钟启动，支持 MySQL/PostgreSQL/MariaDB/SQLite）或本地开发模式。
        </p>
      </div>
    </section>

    <section v-if="!user" class="landing-cta-bottom reveal-on-scroll">
      <p>准备好处理你的第一批文档了吗？</p>
      <div class="hero-cta">
        <router-link v-if="registrationEnabled" class="btn btn-primary" to="/register">立即注册</router-link>
        <router-link class="btn btn-ghost" to="/login">登录已有账号</router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import http from '@/api/http'

const user = ref(null)
const registrationEnabled = ref(true)
const themeClass = ref('theme-dark')
const particleCanvas = ref(null)
let animationId = null
let particles = []
let mouseX = 0
let mouseY = 0
let targetMouseX = 0
let targetMouseY = 0
let revealObserver = null
let mediaQueryList = null

// 粒子类（支持视差效果）
class Particle {
  constructor(canvas) {
    this.canvas = canvas
    this.baseX = Math.random() * canvas.width
    this.baseY = Math.random() * canvas.height
    this.x = this.baseX
    this.y = this.baseY
    this.size = Math.random() * 2 + 0.5
    this.speedX = (Math.random() - 0.5) * 0.3
    this.speedY = (Math.random() - 0.5) * 0.3
    this.opacity = Math.random() * 0.5 + 0.2
    // 视差系数：不同深度的粒子移动速度不同
    this.parallaxFactor = Math.random() * 0.02 + 0.01
  }

  update() {
    // 基础移动
    this.baseX += this.speedX
    this.baseY += this.speedY

    // 边界循环
    if (this.baseX > this.canvas.width) this.baseX = 0
    if (this.baseX < 0) this.baseX = this.canvas.width
    if (this.baseY > this.canvas.height) this.baseY = 0
    if (this.baseY < 0) this.baseY = this.canvas.height

    // 视差效果：根据鼠标位置偏移
    const deltaX = (mouseX - this.canvas.width / 2) * this.parallaxFactor
    const deltaY = (mouseY - this.canvas.height / 2) * this.parallaxFactor

    this.x = this.baseX + deltaX
    this.y = this.baseY + deltaY
  }

  draw(ctx) {
    ctx.fillStyle = `rgba(99, 102, 241, ${this.opacity})`
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
  }
}

function initParticles() {
  const canvas = particleCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  // 创建粒子（增加到150个以增强视觉效果）
  const particleCount = Math.min(150, Math.floor(window.innerWidth * window.innerHeight / 8000))
  particles = []
  for (let i = 0; i < particleCount; i++) {
    particles.push(new Particle(canvas))
  }

  animate()
}

function animate() {
  const canvas = particleCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // 平滑插值鼠标位置
  mouseX += (targetMouseX - mouseX) * 0.1
  mouseY += (targetMouseY - mouseY) * 0.1

  // 更新和绘制粒子
  particles.forEach(particle => {
    particle.update()
    particle.draw(ctx)
  })

  // 绘制连线
  connectParticles(ctx)

  animationId = requestAnimationFrame(animate)
}

function connectParticles(ctx) {
  const maxDistance = 150
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < maxDistance) {
        const opacity = (1 - distance / maxDistance) * 0.2
        ctx.strokeStyle = `rgba(99, 102, 241, ${opacity})`
        ctx.lineWidth = 0.5
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.stroke()
      }
    }
  }
}

function handleMouseMove(e) {
  targetMouseX = e.clientX
  targetMouseY = e.clientY
}

function handleResize() {
  const canvas = particleCanvas.value
  if (canvas) {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    initParticles()
  }
}

function handleThemeChange(e) {
  const isDark = !!e?.matches
  themeClass.value = isDark ? 'theme-dark' : 'theme-light'
}

function initThemeWatch() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
  mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)')
  handleThemeChange(mediaQueryList)
  if (typeof mediaQueryList.addEventListener === 'function') {
    mediaQueryList.addEventListener('change', handleThemeChange)
  } else if (typeof mediaQueryList.addListener === 'function') {
    mediaQueryList.addListener(handleThemeChange)
  }
}

function initRevealObserver() {
  if (typeof window === 'undefined' || typeof window.IntersectionObserver !== 'function') return
  const targets = Array.from(document.querySelectorAll('.reveal-on-scroll'))
  if (!targets.length) return
  targets.forEach((el, idx) => {
    el.style.setProperty('--reveal-delay', `${Math.min(idx * 70, 420)}ms`)
    // 交错飘入：奇偶项轻微左右偏移
    if (idx % 2 === 1) el.classList.add('reveal-from-right')
    else el.classList.add('reveal-from-left')
  })
  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          revealObserver?.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
  )
  targets.forEach((el) => revealObserver.observe(el))
}

onMounted(async () => {
  // 使用 requestAnimationFrame 延迟初始化，避免布局强制
  requestAnimationFrame(() => {
    initParticles()
    initRevealObserver()
  })

  initThemeWatch()
  window.addEventListener('resize', handleResize)
  window.addEventListener('mousemove', handleMouseMove)

  try {
    const { data } = await http.get('/api/settings/public')
    registrationEnabled.value = data.registration_enabled !== false
  } catch {
    /* ignore */
  }

  // 静默检查登录状态（避免未登录时触发 401 控制台噪声）
  try {
    const { data } = await http.get('/api/auth/session')
    if (data?.authenticated && data?.username) {
      user.value = data.username
    } else {
      user.value = null
    }
  } catch (e) {
    console.error('获取会话状态失败:', e.message)
    user.value = null
  }
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('mousemove', handleMouseMove)
  revealObserver?.disconnect()
  if (mediaQueryList) {
    if (typeof mediaQueryList.removeEventListener === 'function') {
      mediaQueryList.removeEventListener('change', handleThemeChange)
    } else if (typeof mediaQueryList.removeListener === 'function') {
      mediaQueryList.removeListener(handleThemeChange)
    }
  }
})
</script>

<style scoped>
.landing-page {
  --glow-primary: rgba(99, 102, 241, 0.9);
  --glow-secondary: rgba(168, 85, 247, 0.85);
  --grid-line: rgba(99, 102, 241, 0.06);
  --hero-chip-bg: rgba(12, 18, 34, 0.65);
  --hero-chip-text: #cfd6ff;
}

.landing-page.theme-light {
  --glow-primary: rgba(79, 70, 229, 0.52);
  --glow-secondary: rgba(217, 70, 239, 0.48);
  --grid-line: rgba(79, 70, 229, 0.12);
  --hero-chip-bg: rgba(248, 250, 252, 0.85);
  --hero-chip-text: #1f2937;
}

.landing-page.theme-dark {
  --glow-primary: rgba(99, 102, 241, 0.9);
  --glow-secondary: rgba(168, 85, 247, 0.85);
  --grid-line: rgba(99, 102, 241, 0.06);
  --hero-chip-bg: rgba(12, 18, 34, 0.65);
  --hero-chip-text: #cfd6ff;
}

/* 全局动画定义 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes driftA {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(26px, 18px) scale(1.05); }
}

@keyframes driftB {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-28px, -14px) scale(1.06); }
}

/* 粒子背景 Canvas */
.particle-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
}

.bg-glow {
  position: fixed;
  border-radius: 999px;
  filter: blur(70px);
  opacity: 0.35;
  pointer-events: none;
  z-index: -2;
}

.bg-glow--one {
  width: 420px;
  height: 420px;
  top: -120px;
  left: -80px;
  background: radial-gradient(circle, var(--glow-primary) 0%, rgba(99, 102, 241, 0) 70%);
  animation: driftA 12s ease-in-out infinite;
}

.bg-glow--two {
  width: 460px;
  height: 460px;
  right: -120px;
  bottom: -100px;
  background: radial-gradient(circle, var(--glow-secondary) 0%, rgba(168, 85, 247, 0) 70%);
  animation: driftB 14s ease-in-out infinite;
}

.bg-grid {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: -3;
  background-image:
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(circle at center, black 30%, transparent 85%);
}

/* Hero 区域样式与动画 */
:deep(.hero) {
  text-align: center;
  padding: 80px 40px 60px; /* 增加左右内边距，从 20px 改为 40px */
  background: linear-gradient(
    135deg,
    rgba(99, 102, 241, 0.08) 0%,
    rgba(168, 85, 247, 0.08) 50%,
    rgba(236, 72, 153, 0.08) 100%
  );
  background-size: 200% 200%;
  animation: gradientShift 15s ease infinite;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  margin: 18px auto 0;
  max-width: 92%;
  backdrop-filter: blur(6px);
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(99, 102, 241, 0.45);
  background: var(--hero-chip-bg);
  color: var(--hero-chip-text);
  font-size: 12px;
  letter-spacing: 0.2px;
  margin-bottom: 18px;
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #34d399, #10b981);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.8);
}

:deep(.hero h1) {
  margin: 0 0 20px;
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--text);
  line-height: 1.2;
  max-width: none; /* 移除最大宽度限制，全屏显示 */
  animation: fadeInUp 0.8s ease-out;
  perspective: 1000px;
}

/* 炫酷标题样式 */
.hero-title {
  position: relative;
  display: inline-block;
  width: 100%;
  cursor: default;
}

.title-text {
  position: relative;
  display: inline-block;
  background: linear-gradient(
    90deg,
    #6366f1 0%,
    #a855f7 25%,
    #ec4899 50%,
    #a855f7 75%,
    #6366f1 100%
  );
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradientFlow 4s linear infinite, float 3s ease-in-out infinite;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.3));
}

/* 鼠标悬停效果 */
.title-text:hover {
  transform: scale(1.05) rotateX(10deg) rotateY(-5deg);
  filter: drop-shadow(0 0 30px rgba(99, 102, 241, 0.6))
          drop-shadow(0 0 60px rgba(168, 85, 247, 0.4));
  animation-play-state: paused;
}

/* 伪元素创建光晕效果 */
.title-text::before {
  content: attr(data-text);
  position: absolute;
  left: 0;
  top: 0;
  z-index: -1;
  background: linear-gradient(
    90deg,
    rgba(99, 102, 241, 0.3) 0%,
    rgba(168, 85, 247, 0.3) 50%,
    rgba(236, 72, 153, 0.3) 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: blur(20px);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.title-text:hover::before {
  opacity: 1;
}

/* 流光动画 */
@keyframes gradientFlow {
  0% {
    background-position: 0% center;
  }
  100% {
    background-position: 200% center;
  }
}

/* 浮动动画 */
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

:deep(.hero p) {
  margin: 0 auto 32px;
  max-width: none; /* 移除最大宽度限制，全屏显示 */
  padding: 0 5%; /* 添加适当的左右内边距，避免贴边 */
  font-size: 1.1rem;
  line-height: 1.7;
  color: var(--text-muted);
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

:deep(.hero-cta) {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.hero-stats {
  margin-top: 26px;
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 12px;
  max-width: 860px;
  margin-left: auto;
  margin-right: auto;
}

.reveal-on-scroll {
  opacity: 0;
  transform: translate3d(0, 42px, 0) scale(0.965);
  filter: blur(8px);
  transition:
    opacity 0.72s cubic-bezier(0.2, 0.7, 0.2, 1),
    transform 0.72s cubic-bezier(0.2, 0.7, 0.2, 1),
    filter 0.72s cubic-bezier(0.2, 0.7, 0.2, 1);
  transition-delay: var(--reveal-delay, 0ms);
  will-change: opacity, transform, filter;
}

.reveal-on-scroll.is-visible {
  opacity: 1;
  transform: translate3d(0, 0, 0) scale(1);
  filter: blur(0);
}

.reveal-on-scroll.reveal-from-left {
  transform: translate3d(-28px, 42px, 0) scale(0.965);
}

.reveal-on-scroll.reveal-from-right {
  transform: translate3d(28px, 42px, 0) scale(0.965);
}

.hero-stat {
  background: rgba(10, 16, 30, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 14px 12px;
  backdrop-filter: blur(8px);
  transition: transform 0.25s ease, border-color 0.25s ease;
}

.hero-stat:hover {
  transform: translateY(-3px);
  border-color: rgba(99, 102, 241, 0.55);
}

.hero-stat strong {
  display: block;
  font-size: 20px;
  line-height: 1.2;
  color: #eef2ff;
}

.hero-stat span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #bfc8dc;
}

.landing-block {
  max-width: 75%;
  margin: 0 auto;
  padding: 60px 20px; /* 统一上下内边距为 60px */
  animation: fadeInUp 0.8s ease-out;
  animation-fill-mode: both;
}

/* 交替背景色，增加视觉层次 */
.landing-block:nth-child(odd) {
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.03) 0%, transparent 100%);
}

.landing-block:nth-child(even) {
  background: linear-gradient(180deg, rgba(168, 85, 247, 0.03) 0%, transparent 100%);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .landing-block {
    max-width: 95%; /* 移动端使用更宽的宽度 */
    padding: 40px 16px; /* 减小内边距 */
  }

  .landing-block--narrow {
    max-width: 95%;
    padding: 35px 16px;
  }

  .landing-cta-bottom {
    max-width: 95%;
    padding: 40px 16px 60px;
  }

  /* 移动端标题优化 */
  :deep(.hero h1) {
    font-size: 1.8rem;
  }

  .title-text:hover {
    transform: scale(1.02);
    filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.5));
  }

  .hero-stats {
    grid-template-columns: 1fr;
    max-width: 92%;
  }

  .reveal-on-scroll {
    opacity: 1;
    transform: none;
  }
}

.landing-block:nth-child(2) { animation-delay: 0.1s; }
.landing-block:nth-child(3) { animation-delay: 0.2s; }
.landing-block:nth-child(4) { animation-delay: 0.3s; }
.landing-block:nth-child(5) { animation-delay: 0.4s; }
.landing-block:nth-child(6) { animation-delay: 0.5s; }

.landing-block--narrow {
  max-width: 75%;
  padding: 50px 20px; /* 窄板块稍小的内边距 */
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
  border-radius: 16px;
  margin-bottom: 20px;
}
.landing-title {
  margin: 0 0 12px; /* 增加底部间距 */
  font-size: 1.5rem; /* 增大标题字号 */
  font-weight: 800; /* 加粗 */
  color: var(--text);
  text-align: center;
  position: relative;
  display: inline-block;
  width: 100%;
  letter-spacing: -0.02em; /* 稍微收紧字距 */
}
.landing-title::after {
  content: '';
  display: block;
  width: 60px;
  height: 3px;
  margin: 12px auto 0;
  background: linear-gradient(90deg, var(--accent), var(--accent-dim));
  border-radius: 2px;
  animation: expandWidth 1s ease-out 0.5s both;
}

@keyframes expandWidth {
  from {
    width: 0;
  }
  to {
    width: 60px;
  }
}
.landing-sub {
  margin: 0 auto 28px; /* 增加底部间距 */
  max-width: 640px;
  text-align: center;
  font-size: 15px; /* 稍微增大字号 */
  line-height: 1.7;
  color: var(--text-muted);
}
.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.step {
  position: relative;
  margin: 0;
  padding: 20px 18px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
}
.step h3 {
  margin: 0 0 8px;
  font-size: 1rem;
  color: var(--accent);
}
.step p {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--text-muted);
}
.step-num {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #061018;
  background: linear-gradient(135deg, var(--accent), var(--accent-dim));
}
.landing-detail {
  padding: 32px 36px; /* 增加内边距 */
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px; /* 增大圆角 */
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  /* 移除 fadeIn 动画，避免文字闪烁 */
}
.landing-detail:hover {
  border-color: var(--accent);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2);
  transform: translateY(-2px);
}
.landing-detail p {
  margin: 0 0 16px; /* 增加底部间距 */
  font-size: 15px; /* 增大字号 */
  line-height: 1.75; /* 增加行高 */
  color: var(--text-muted);
  position: relative;
  padding-left: 20px;
}
/* 为每个段落添加小圆点装饰 */
.landing-detail p::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-dim));
}
.landing-detail p:last-child {
  margin-bottom: 0;
}
.landing-detail strong {
  color: var(--text);
  font-weight: 600;
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px; /* 增加间距 */
  margin-top: 32px; /* 增加顶部间距 */
}
.feature {
  padding: 28px 24px; /* 增加内边距 */
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px; /* 增大圆角 */
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: default;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 200px; /* 增加最小高度 */
  transform-style: preserve-3d;
}

/* 特性图标样式 */
.feature-icon {
  font-size: 3.5rem;
  margin-bottom: 16px;
  display: inline-block;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

/* 所有图标统一的悬停效果 */
.feature:hover .feature-icon {
  transform: scale(1.15) translateY(-6px);
  filter: drop-shadow(0 8px 16px rgba(99, 102, 241, 0.4));
}

/* 不同图标的独特动画 - 统一风格，避免过度眩晕 */
.icon-brain {
  animation: pulse 2.5s ease-in-out infinite;
}

.icon-crop {
  animation: subtle-rotate 3s ease-in-out infinite;
}

.icon-palette {
  animation: bounce 2.5s ease-in-out infinite;
}

.icon-package {
  animation: slide-up-down 2.5s ease-in-out infinite;
}

.icon-bolt {
  animation: flash 2s ease-in-out infinite;
}

.icon-shield {
  animation: shield-pulse 2.5s ease-in-out infinite;
}

.icon-rocket {
  animation: rocket-fly 3s ease-in-out infinite;
}

.icon-globe {
  animation: globe-pulse 3s ease-in-out infinite;
}

.icon-database {
  animation: database-pulse 2.5s ease-in-out infinite;
}

.icon-lock {
  animation: lock-sway 3s ease-in-out infinite;
}

.icon-settings {
  animation: settings-bounce 3s ease-in-out infinite;
}

.icon-chart {
  animation: chart-grow 2.5s ease-in-out infinite;
}

.icon-book {
  animation: book-flip 3s ease-in-out infinite;
}

.icon-briefcase {
  animation: briefcase-bounce 2.5s ease-in-out infinite;
}

.icon-graduation {
  animation: graduation-bounce 2.5s ease-in-out infinite;
}

.icon-archive {
  animation: archive-slide 3s ease-in-out infinite;
}

.icon-flask {
  animation: flask-bubble 2.5s ease-in-out infinite;
}

.icon-newspaper {
  animation: newspaper-float 3s ease-in-out infinite;
}

/* 各种动画关键帧 - 统一风格，避免过度眩晕 */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.08);
  }
}

@keyframes subtle-rotate {
  0%, 100% {
    transform: rotate(0deg);
  }
  50% {
    transform: rotate(10deg);
  }
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes slide-up-down {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes flash {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.75;
    transform: scale(1.1);
  }
}

@keyframes shield-pulse {
  0%, 100% {
    transform: scale(1) rotate(0deg);
  }
  50% {
    transform: scale(1.06) rotate(3deg);
  }
}

@keyframes rocket-fly {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  25% {
    transform: translateY(-6px) rotate(-3deg);
  }
  75% {
    transform: translateY(-3px) rotate(3deg);
  }
}

@keyframes gentle-rotate {
  0%, 100% {
    transform: scale(1) rotate(0deg);
  }
  50% {
    transform: scale(1.05) rotate(5deg);
  }
}

@keyframes globe-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.08);
  }
}

@keyframes database-pulse {
  0%, 100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.08);
  }
}

@keyframes lock-sway {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-5deg);
  }
  75% {
    transform: rotate(5deg);
  }
}

@keyframes settings-rotate {
  0%, 100% {
    transform: scale(1) rotate(0deg);
  }
  50% {
    transform: scale(1.06) rotate(8deg);
  }
}

@keyframes settings-bounce {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-6px) rotate(5deg);
  }
}

@keyframes chart-grow {
  0%, 100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.1);
  }
}

@keyframes book-flip {
  0%, 100% {
    transform: rotateY(0deg);
  }
  50% {
    transform: rotateY(15deg);
  }
}

@keyframes briefcase-bounce {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-6px) rotate(5deg);
  }
}

@keyframes graduation-bounce {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-8px) rotate(8deg);
  }
}

@keyframes archive-slide {
  0%, 100% {
    transform: translateX(0);
  }
  50% {
    transform: translateX(5px);
  }
}

@keyframes flask-bubble {
  0%, 100% {
    transform: scale(1) rotate(0deg);
  }
  50% {
    transform: scale(1.08) rotate(-8deg);
  }
}

@keyframes newspaper-float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-5px) rotate(3deg);
  }
}
.feature::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent
  );
  transition: left 0.5s ease;
}
.feature:hover::before {
  left: 100%;
}
.feature:hover {
  transform: translateY(-6px) scale(1.02) rotateX(2deg) rotateY(-1deg);
  box-shadow: 0 16px 40px rgba(99, 102, 241, 0.25);
  border-color: var(--accent);
}
.feature h3 {
  margin: 0 0 12px; /* 增加底部间距 */
  font-size: 1.1rem; /* 增大字号 */
  font-weight: 700;
  color: var(--accent);
  transition: transform 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0; /* 移除 gap，因为图标已独立 */
}
.feature:hover h3 {
  transform: translateX(4px);
}
.feature p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-muted);
  transition: color 0.3s ease;
  flex: 1; /* 让文字区域自动填充剩余空间 */
}
.feature:hover p {
  color: var(--text);
}
.landing-cta-bottom {
  text-align: center;
  padding: 60px 20px 80px; /* 增加上下内边距 */
  max-width: 75%;
  margin: 0 auto;
  animation: fadeInUp 0.8s ease-out 0.6s both;
  background: linear-gradient(180deg, transparent 0%, rgba(99, 102, 241, 0.05) 100%); /* 添加渐变背景 */
}
.landing-cta-bottom p {
  margin: 0 0 20px; /* 增加底部间距 */
  font-size: 16px; /* 增大字号 */
  font-weight: 600; /* 加粗 */
  color: var(--text); /* 使用主文字颜色 */
  animation: float 3s ease-in-out infinite;
}

/* 按钮动效增强 */
:deep(.btn) {
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.btn::before) {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s ease, height 0.6s ease;
}

:deep(.btn:hover::before) {
  width: 300px;
  height: 300px;
}

:deep(.btn:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
}

:deep(.btn-primary:hover) {
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
}

:deep(.hero-cta .btn-primary) {
  position: relative;
  isolation: isolate;
}

:deep(.hero-cta .btn-primary::after) {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: inherit;
  z-index: -1;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.45) 0%, rgba(99, 102, 241, 0) 72%);
  animation: ctaPulse 2.6s ease-in-out infinite;
}

@keyframes ctaPulse {
  0%, 100% {
    opacity: 0.28;
    transform: scale(0.96);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.05);
  }
}

:deep(.btn-ghost:hover) {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--accent);
}

/* 顶部导航栏动效 */
:deep(.topbar) {
  animation: fadeIn 0.6s ease-out;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

:deep(.brand) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 1.2rem;
  color: var(--text);
  text-decoration: none;
  transition: all 0.3s ease;
}

:deep(.brand:hover) {
  transform: scale(1.05);
  color: var(--accent);
}

:deep(.brand-mark) {
  display: inline-block;
  animation: float 3s ease-in-out infinite;
  font-size: 1.4rem;
}

/* 平滑滚动 */
html {
  scroll-behavior: smooth;
}

/* 自定义滚动条样式（webkit 浏览器） */
::-webkit-scrollbar {
  width: 10px;
}

::-webkit-scrollbar-track {
  background: #0c1222; /* 深色背景，与项目主题一致 */
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--accent), var(--accent-dim));
  border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}
</style>
