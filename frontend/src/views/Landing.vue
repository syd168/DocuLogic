<template>
  <div>
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
      <h1 class="hero-title">
        <span class="title-text" data-text="智能文档解析平台">智能文档解析平台</span>
      </h1>
      <p>
        基于 <strong>Qwen3-VL</strong> 多模态大模型与 <strong>Logics-Parsing-v2</strong> 引擎，将扫描件、截图与 PDF 精准转换为结构化 Markdown：
        智能识别文本、表格、公式、流程图、化学式、乐谱等复杂元素，支持<strong>图像精确裁剪</strong>、<strong>三种输出模式</strong>与<strong>批量下载</strong>，
        完美适配知识库构建、二次编辑与企业级文档自动化处理流程。
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
    </section>

    <section class="landing-block">
      <h2 class="landing-title">核心特色</h2>
      <p class="landing-sub">融合前沿 AI 技术与工程化实践，提供企业级文档解析能力。</p>
      <div class="features">
        <div class="feature">
          <div class="feature-icon icon-brain">🧠</div>
          <h3>Qwen3-VL 多模态理解</h3>
          <p>精准识别文本、表格、公式、流程图、化学式等专业内容</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-crop">✂️</div>
          <h3>智能图像裁剪</h3>
          <p>像素级精确裁剪图片区域，支持任意分辨率</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-palette">🎨</div>
          <h3>三种输出模式</h3>
          <p>Base64 嵌入 / 独立文件 / 不输出，灵活配置</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-package">📦</div>
          <h3>ZIP 打包与批量下载</h3>
          <p>自动生成完整 ZIP 包，支持批量一键下载</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-bolt">⚡</div>
          <h3>实时进度与可控中断</h3>
          <p>WebSocket 实时推送，支持中途停止并保存结果</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-shield">🔐</div>
          <h3>企业级权限与安全</h3>
          <p>JWT 认证、bcrypt 加密、速率限制、数据隔离</p>
        </div>
      </div>
    </section>

    <section class="landing-block">
      <h2 class="landing-title">技术架构</h2>
      <p class="landing-sub">现代化全栈设计，兼顾性能、安全与可扩展性。</p>
      <div class="features">
        <div class="feature">
          <div class="feature-icon icon-rocket">🚀</div>
          <h3>高性能推理引擎</h3>
          <p>CUDA BF16 加速 + SDPA 优化，OmniDocBench 得分 93.23</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-globe">🌐</div>
          <h3>FastAPI + Vue 3</h3>
          <p>前后端分离，REST API + WebSocket 双通道通信</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-database">🗄️</div>
          <h3>MySQL/SQLite 灵活切换</h3>
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
          <p>环境变量 + 管理后台双重配置，动态调整参数</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-chart">📊</div>
          <h3>完善的日志与监控</h3>
          <p>详细运行日志，僵尸任务自动检测与恢复</p>
        </div>
      </div>
    </section>

    <section class="landing-block">
      <h2 class="landing-title">应用场景</h2>
      <p class="landing-sub">适用于多种文档类型与业务场景，助力知识管理与自动化流程。</p>
      <div class="features">
        <div class="feature">
          <div class="feature-icon icon-book">📚</div>
          <h3>学术研究与知识库</h3>
          <p>论文明表结构化，导入 Obsidian/Notion</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-briefcase">💼</div>
          <h3>企业文档数字化</h3>
          <p>财报合同扫描件还原，批量上传一键下载</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-graduation">🎓</div>
          <h3>教育培训资料整理</h3>
          <p>课件截图转大纲，Mermaid 流程图自动识别</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-archive">🏛️</div>
          <h3>档案管理与合规</h3>
          <p>票据表单批量处理，全文检索对接业务系统</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-flask">🔬</div>
          <h3>STEM 科研数据处理</h3>
          <p>化学式、数学公式、物理图表精准识别</p>
        </div>
        <div class="feature">
          <div class="feature-icon icon-newspaper">📰</div>
          <h3>媒体内容管理</h3>
          <p>新闻稿件快速数字化，CMS 无缝集成</p>
        </div>
      </div>
    </section>

    <section class="landing-block landing-block--narrow">
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
          <strong>STEM 专业内容：</strong>特别优化对数学公式、化学分子式、物理图表、生物图谱、乐谱、手写文本等专业领域内容的识别与转换。
        </p>
      </div>
    </section>

    <section class="landing-block landing-block--narrow">
      <h2 class="landing-title">输出与对接</h2>
      <div class="landing-detail">
        <p>
          每个任务产出包含：<strong>Markdown 文件</strong>（.mmd，清洗后的最终版本）、<strong>原始输出</strong>（_raw.mmd，模型直接生成的 HTML）、<strong>可视化图</strong>（_vis.png 或 _vis.zip，带 bbox 标注）以及可选的 <strong>assets 文件夹</strong>（裁剪出的独立图片）。
        </p>
        <p>
          支持三种图片输出模式：<strong>base64</strong>（内嵌到 Markdown）、<strong>separate</strong>（独立文件 + ZIP 打包）、<strong>none</strong>（不输出图片）。管理员可配置全局默认值，用户也可设置个人偏好。
        </p>
        <p>
          Web 服务提供完整的 <strong>REST API</strong>（上传、查询、下载、停止、删除）与 <strong>WebSocket 实时推送</strong>能力，可与内部审批流、知识库索引、CI/CD 流水线等系统组合；生产环境请配置 JWT、HTTPS 与合理的速率限制。
        </p>
        <p>
          支持 <strong>Docker 一键部署</strong>（包含主应用 + Redis + MySQL），5 分钟即可启动；也支持本地开发模式，适合调试与定制开发。
        </p>
      </div>
    </section>

    <section v-if="!user" class="landing-cta-bottom">
      <p>准备好处理你的第一批文档了吗？</p>
      <div class="hero-cta">
        <router-link v-if="registrationEnabled" class="btn btn-primary" to="/register">立即注册</router-link>
        <router-link class="btn btn-ghost" to="/login">登录已有账号</router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import http from '@/api/http'

const user = ref(null)
const registrationEnabled = ref(true)

onMounted(async () => {
  try {
    const { data } = await http.get('/api/settings/public')
    registrationEnabled.value = data.registration_enabled !== false
  } catch {
    /* ignore */
  }
  try {
    const { data } = await http.get('/api/auth/me')
    if (data?.username) user.value = data.username
  } catch {
    user.value = null
  }
})
</script>

<style scoped>
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
}

.landing-block:nth-child(2) { animation-delay: 0.1s; }
.landing-block:nth-child(3) { animation-delay: 0.2s; }
.landing-block:nth-child(4) { animation-delay: 0.3s; }
.landing-block:nth-child(5) { animation-delay: 0.4s; }
.landing-block:nth-child(6) { animation-delay: 0.5s; }

.landing-block--narrow {
  max-width: 75%;
  padding: 50px 20px; /* 窄板块稍小的内边距 */
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
  padding: 28px 32px; /* 增加内边距 */
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px; /* 增大圆角 */
  transition: all 0.3s ease;
  animation: fadeIn 0.8s ease-out 0.6s both;
}
.landing-detail:hover {
  border-color: var(--accent);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.15);
  transform: translateY(-2px);
}
.landing-detail p {
  margin: 0 0 16px; /* 增加底部间距 */
  font-size: 15px; /* 增大字号 */
  line-height: 1.75; /* 增加行高 */
  color: var(--text-muted);
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
}

/* 特性图标样式 */
.feature-icon {
  font-size: 3.5rem;
  margin-bottom: 16px;
  display: inline-block;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

/* 不同图标的独特动画 */
.icon-brain {
  animation: pulse 2s ease-in-out infinite;
}

.icon-crop {
  animation: rotate-slow 8s linear infinite;
}

.icon-palette {
  animation: bounce 2s ease-in-out infinite;
}

.icon-package {
  animation: slide-up-down 2.5s ease-in-out infinite;
}

.icon-bolt {
  animation: flash 1.5s ease-in-out infinite;
}

.icon-shield {
  animation: shield-pulse 2s ease-in-out infinite;
}

.icon-rocket {
  animation: rocket-fly 3s ease-in-out infinite;
}

.icon-globe {
  animation: spin 10s linear infinite;
}

.icon-database {
  animation: database-pulse 2s ease-in-out infinite;
}

.icon-lock {
  animation: lock-shake 3s ease-in-out infinite;
}

.icon-settings {
  animation: settings-rotate 6s linear infinite;
}

.icon-chart {
  animation: chart-grow 2s ease-in-out infinite;
}

.icon-book {
  animation: book-flip 3s ease-in-out infinite;
}

.icon-briefcase {
  animation: briefcase-swing 2.5s ease-in-out infinite;
}

.icon-graduation {
  animation: graduation-bounce 2s ease-in-out infinite;
}

.icon-archive {
  animation: archive-slide 3s ease-in-out infinite;
}

.icon-flask {
  animation: flask-bubble 2s ease-in-out infinite;
}

.icon-newspaper {
  animation: newspaper-flutter 2.5s ease-in-out infinite;
}

/* 图标悬停效果 */
.feature:hover .feature-icon {
  transform: scale(1.2) translateY(-8px);
  filter: drop-shadow(0 8px 16px rgba(99, 102, 241, 0.4));
}

/* 各种动画关键帧 */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

@keyframes rotate-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes slide-up-down {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-12px);
  }
}

@keyframes flash {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.15);
  }
}

@keyframes shield-pulse {
  0%, 100% {
    transform: scale(1) rotate(0deg);
  }
  50% {
    transform: scale(1.08) rotate(5deg);
  }
}

@keyframes rocket-fly {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  25% {
    transform: translateY(-8px) rotate(-5deg);
  }
  75% {
    transform: translateY(-4px) rotate(5deg);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes database-pulse {
  0%, 100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.1);
  }
}

@keyframes lock-shake {
  0%, 100% {
    transform: rotate(0deg);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: rotate(-5deg);
  }
  20%, 40%, 60%, 80% {
    transform: rotate(5deg);
  }
}

@keyframes settings-rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes chart-grow {
  0%, 100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.15);
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

@keyframes briefcase-swing {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-8deg);
  }
  75% {
    transform: rotate(8deg);
  }
}

@keyframes graduation-bounce {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-10px) rotate(10deg);
  }
}

@keyframes archive-slide {
  0%, 100% {
    transform: translateX(0);
  }
  50% {
    transform: translateX(8px);
  }
}

@keyframes flask-bubble {
  0%, 100% {
    transform: scale(1) rotate(0deg);
  }
  50% {
    transform: scale(1.1) rotate(-10deg);
  }
}

@keyframes newspaper-flutter {
  0%, 100% {
    transform: skewX(0deg);
  }
  50% {
    transform: skewX(5deg);
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
  transform: translateY(-4px) scale(1.02);
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
