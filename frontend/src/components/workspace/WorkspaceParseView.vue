<template>
  <div class="view-panel">
    <div class="container card parse-container">
      <div class="page-header">
        <h1>
          <span class="page-icon">📄</span>
          文档解析
        </h1>
      </div>
      <div class="parse-page-intro">
        <p class="parse-page-lead" v-if="adminForm.allow_multi_file_upload">
          添加图片或 PDF，支持多选与多次添加；解析前可从队列移除或清空。按顺序逐个处理，每个文件一条生成记录，进行中可停止。
        </p>
        <p class="parse-page-note" v-else>
          添加图片或 PDF，但仅支持上传一个文件，即一个文件一条生成记录，进行中可选择停止。
        </p>

        <span class="parse-formats-label">支持格式：PNG、JPG、WebP、BMP、TIFF、PDF</span>

        <p class="parse-page-note muted">
          PDF 按页解析，每个文件最多解析页数受账号上限约束；可在下方滑动条指定单个文件的解析页数。
          <span v-if="pdfPageCountLoading" style="color: #e6a23c; font-weight: 500;">（正在读取 PDF 页数…）</span>
        </p>
        <details class="parse-page-details">
          <summary>输出文件说明</summary>
          <ul class="parse-page-details-list">
            <li>多页 PDF 的可视化结果为 <strong>ZIP</strong>；单图或单页为 <strong>PNG</strong>。</li>
            <li>
              文本：<code>*_raw.md</code> 为模型直出；<code>*.md</code> 为经
              <code>qwenvl_cast_html_tag</code> 转换后的结果。
            </li>
          </ul>
        </details>
      </div>

      <div class="upload-area" :class="{ dragover: dragOver }" tabindex="0" role="button" @click="fileInputEl?.click()"
        @dragenter.prevent="dragOver = true" @dragover.prevent="dragOver = true" @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop">
        <input ref="fileInputEl" type="file" class="hidden-file" :multiple="adminForm.allow_multi_file_upload"
          accept=".png,.jpg,.jpeg,.bmp,.tiff,.webp,.pdf,image/*,application/pdf" @change="onFilePick" />
        <div class="upload-icon" aria-hidden="true">📄</div>
        <div class="upload-hint">
          将文件拖到此处，或 <em>点击选择</em>
          <span v-if="adminForm.allow_multi_file_upload">（可多选，可多次添加）</span>
          <span v-else>（每次只能选择一个文件）</span>
        </div>
        <div class="file-meta">{{ fileLabel }}</div>
      </div>

      <div v-if="parseQueue.length" class="parse-queue card">
        <div class="parse-queue-toolbar">
          <span class="parse-queue-title">待解析列表（{{ parseQueue.length }}）</span>
          <el-button size="small" text type="danger" :disabled="parsing" @click="clearParseQueue">清空</el-button>
        </div>
        <ul class="parse-queue-list">
          <li v-for="q in parseQueue" :key="q.id" class="parse-queue-item">
            <span class="parse-queue-name" :title="q.file.name">{{ q.file.name }}</span>
            <span v-if="isPdfFileName(q.file.name)" class="parse-queue-pdf-meta"
              :class="{ 'pdf-loading': q.pdfNumPages === undefined, 'pdf-error': q.pdfError }">
              <template v-if="q.pdfNumPages === undefined">⏳ 正在读取页数…</template>
              <template v-else-if="typeof q.pdfNumPages === 'number'">📄 共 {{ q.pdfNumPages }} 页</template>
              <template v-else-if="q.pdfError">❌ {{ q.pdfError }}</template>
              <template v-else>❓ 页数未知（解析时按文件实际页数截断）</template>
            </span>
            <span v-else class="parse-queue-pdf-meta muted">计 1 页</span>
            <span class="muted parse-queue-kb">{{ Math.round(q.file.size / 1024) }} KB</span>
            <el-button link type="danger" size="small" :disabled="parsing" @click="removeQueueItem(q.id)">
              移除
            </el-button>
          </li>
        </ul>
      </div>

      <label class="field parse-prompt-field">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
          <span>解析提示词（可选）</span>
          <el-tooltip placement="top" effect="dark">
            <template #content>
              <div style="max-width: 360px; line-height: 1.6;">
                <div style="font-weight: 600; margin-bottom: 8px;">💡 什么是解析提示词？</div>
                <div style="margin-bottom: 8px;">与图像一起送入多模态模型的<strong>文字指令</strong>，用于说明解析任务与期望的输出形式。</div>
                <div>• 留空时使用默认「QwenVL HTML」</div>
                <div>• 可在默认效果不理想时尝试自定义指令</div>
              </div>
            </template>
            <span style="cursor: help; font-size: 16px; opacity: 0.6;">❓</span>
          </el-tooltip>
        </div>
        <el-input :model-value="prompt" clearable placeholder="留空则使用默认：QwenVL HTML"
          @update:model-value="$emit('update:prompt', $event)" />
        <details class="parse-page-details parse-prompt-details">
          <summary>推荐示例（点击填入输入框）</summary>
          <ul class="parse-page-details-list parse-prompt-example-list">
            <li>
              <button type="button" class="parse-prompt-pick" @click="setParsePromptExample('QwenVL HTML')">
                QwenVL HTML
              </button>
              <span class="muted">项目默认，适合版面转 HTML，与后续转换流程配套。</span>
            </li>
            <li>
              <button type="button" class="parse-prompt-pick"
                @click="setParsePromptExample('请识别图像中的文字与版面结构，输出为 HTML。')">
                任务说明
              </button>
              <span class="muted">明确「识别什么、输出什么」，可在默认效果不理想时尝试。</span>
            </li>
          </ul>
        </details>
      </label>

      <div v-show="hasQueue" class="field pdf-pages-field">
        <div class="pdf-pages-header">
          <span class="pdf-pages-label">📄 单个文件解析页数</span>
          <el-tooltip placement="top" effect="dark">
            <template #content>
              <div style="max-width: 320px; line-height: 1.6;">
                <div style="font-weight: 600; margin-bottom: 8px;">💡 使用说明</div>
                <div>• 滑动条最大值 = min(您的上限, 单个文件最大页数)</div>
                <div>• PDF 按实际页数计算，图片每张计 1 页</div>
                <div>• 仅对队列中的 PDF 生效</div>
              </div>
            </template>
            <span class="pdf-pages-help-icon" aria-label="帮助">❓</span>
          </el-tooltip>
        </div>

        <div class="pdf-pages-slider-wrap">
          <div class="pdf-pages-slider-head">
            <div class="pdf-pages-input-row" aria-live="polite">
              <el-input-number :model-value="pdfPagesRequested" class="pdf-pages-input-num" :min="1"
                :max="pdfPagesSliderMax" :step="1" :precision="0" :disabled="!hasQueue || parsing"
                controls-position="right" @change="clampPdfPagesRequested"
                @update:model-value="$emit('update:pdf-pages-requested', $event)" />
              <span class="pdf-pages-current-unit">页</span>
              <span v-if="queueTotalPages != null" class="pdf-pages-total-badge">
                共 {{ queueTotalPages }} 页
              </span>
              <span v-else-if="pdfPageCountLoading" class="pdf-pages-loading-badge">
                <span class="loading-dots">读取中</span>
              </span>
            </div>
            <el-slider :model-value="pdfPagesRequested" class="pdf-pages-slider-el" :min="1" :max="pdfPagesSliderMax"
              :step="1" :disabled="!hasQueue || parsing" :format-tooltip="formatPdfPagesTooltip" :show-tooltip="true"
              @update:model-value="$emit('update:pdf-pages-requested', $event)" />
          </div>
          <div class="pdf-pages-slider-feet">
            <span class="pdf-pages-range-min">1</span>
            <span class="muted pdf-pages-hint">
              <template v-if="pdfPageCountLoading">⏳ 正在读取 PDF 页数…</template>
              <template v-else-if="queueTotalPages != null">
                上限 {{ pdfPagesMax }} 页 · 单文件最大 {{ pdfPagesSliderMax }} 页
              </template>
              <template v-else>
                上限 {{ pdfPagesMax }} 页
              </template>
            </span>
            <span class="pdf-pages-range-max">{{ pdfPagesSliderMax }}</span>
          </div>
        </div>
      </div>

      <div class="btn-row btn-row-split">
        <el-button type="primary" :disabled="!hasQueue || parsing" @click="startParse">开始解析</el-button>
        <el-button v-show="showStop" class="btn-danger-outline" :disabled="!currentJobId" @click="stopJob">
          停止生成
        </el-button>
      </div>

      <div v-show="showProgress" class="progress-container">
        <el-progress :percentage="progressPct" :stroke-width="16" />
        <p class="progress-msg">{{ progressMsg }}</p>
      </div>

      <el-alert v-if="parseErr" :title="parseErr" type="error" show-icon :closable="false" style="margin-top: 16px" />

      <div v-show="showResult" class="result-files">
        <h3>处理结果</h3>
        <p v-if="resultPartial" class="muted">
          本次为部分结果（中途停止）。单张图任务仅在推理开始前可停止；PDF 可在页与页之间停止。
        </p>
        <template v-if="parseBatchResults.length > 1">
          <p class="muted">以下为本次依次解析的各个任务（均已写入生成记录）。</p>
          <div v-for="(br, bidx) in parseBatchResults" :key="bidx" class="batch-result-block">
            <template v-if="br.ok">
              <div class="batch-result-title">{{ br.filename }}</div>
              <a v-for="item in batchFileLinks(br.job_id)" :key="item.path" class="file-link" :href="item.path"
                target="_blank" rel="noopener">
                下载 {{ item.name }}
              </a>
            </template>
            <div v-else class="batch-result-err">{{ br.filename }}：{{ br.error }}</div>
          </div>
        </template>
        <template v-else>
          <a v-for="item in resultLinks" :key="item.path" class="file-link" :href="item.path" target="_blank"
            rel="noopener">
            下载 {{ item.name }}
          </a>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const fileInputEl = ref(null)

defineProps({
  adminForm: { type: Object, required: true },
  pdfPageCountLoading: { type: Boolean, required: true },
  dragOver: { type: Boolean, required: true },
  onDrop: { type: Function, required: true },
  onFilePick: { type: Function, required: true },
  fileLabel: { type: String, required: true },
  parseQueue: { type: Array, required: true },
  parsing: { type: Boolean, required: true },
  clearParseQueue: { type: Function, required: true },
  isPdfFileName: { type: Function, required: true },
  removeQueueItem: { type: Function, required: true },
  hasQueue: { type: Boolean, required: true },
  prompt: { type: String, required: true },
  setParsePromptExample: { type: Function, required: true },
  pdfPagesRequested: { type: Number, required: true },
  pdfPagesSliderMax: { type: Number, required: true },
  clampPdfPagesRequested: { type: Function, required: true },
  queueTotalPages: { type: Number, default: null },
  formatPdfPagesTooltip: { type: Function, required: true },
  pdfPagesMax: { type: Number, required: true },
  startParse: { type: Function, required: true },
  showStop: { type: Boolean, required: true },
  currentJobId: { type: [String, Number], default: '' },
  stopJob: { type: Function, required: true },
  showProgress: { type: Boolean, required: true },
  progressPct: { type: Number, required: true },
  progressMsg: { type: String, required: true },
  parseErr: { type: String, default: '' },
  showResult: { type: Boolean, required: true },
  resultPartial: { type: Boolean, required: true },
  parseBatchResults: { type: Array, required: true },
  batchFileLinks: { type: Function, required: true },
  resultLinks: { type: Array, required: true },
})

defineEmits(['update:prompt', 'update:pdf-pages-requested'])
</script>
