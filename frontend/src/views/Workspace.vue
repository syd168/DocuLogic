<template>
  <div class="workspace-layout" :class="{ 'is-mobile': isMobile }">
    <div v-if="isMobile && mobileNavOpen" class="workspace-sider-backdrop" aria-hidden="true"
      @click="mobileNavOpen = false" />
    <aside class="workspace-sider" :class="{ 'is-open': !isMobile || mobileNavOpen }">
      <div class="sider-brand">
        <router-link class="brand" to="/app" @click="onSiderBrandClick"><span class="brand-mark">📄</span>
          DocuLogic</router-link>
        <button v-if="isMobile" type="button" class="sider-close-btn" aria-label="关闭菜单" @click="mobileNavOpen = false">
          ×
        </button>
      </div>
      <el-menu class="sider-menu" :default-active="activeMenu" background-color="transparent"
        text-color="var(--text-muted)" active-text-color="var(--accent)" @select="onMenuSelect">
        <el-menu-item index="parse">
          <span class="menu-icon">📄</span>
          <span>文档解析</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="settings">
          <span class="menu-icon">⚙️</span>
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item index="profile">
          <span class="menu-icon">👤</span>
          <span>个人中心</span>
        </el-menu-item>
        <el-menu-item index="records">
          <span class="menu-icon">📋</span>
          <span>生成记录</span>
        </el-menu-item>
        <el-menu-item index="cache">
          <span class="menu-icon">🗑️</span>
          <span>缓存清除</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="users">
          <span class="menu-icon">👥</span>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <div class="workspace-main">
      <header class="workspace-header">
        <div class="workspace-header-left">
          <button v-if="isMobile" type="button" class="nav-toggle" aria-label="打开菜单" :aria-expanded="mobileNavOpen"
            @click="mobileNavOpen = !mobileNavOpen">
            <span class="nav-toggle-bars" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </span>
          </button>
          <span class="workspace-header-title">{{ menuTitle }}</span>
        </div>
        <div class="workspace-header-actions">
          <router-link to="/" class="home-link" title="返回首页">
            <span class="home-icon">🏠</span>
            <span class="home-text">首页</span>
          </router-link>
          <span class="user-pill">已登录：<strong>{{ username }}</strong></span>
          <el-button class="btn-ghost" link type="info" @click="logout">退出</el-button>
        </div>
      </header>
      <div class="workspace-body">
        <!-- 文档解析 -->
        <div v-show="activeMenu === 'parse'" class="view-panel">
          <div class="container card parse-container">
            <div class="page-header">
              <h1>
                <span class="page-icon">📄</span>
                文档解析
              </h1>
            </div>
            <div class="parse-page-intro">
              <p class="parse-page-lead">
                添加图片或 PDF，支持多选与多次添加；解析前可从队列移除或清空。按顺序逐个处理，每个文件一条生成记录，进行中可停止。
              </p>
              <div class="parse-formats">
                <span class="parse-formats-label">支持格式</span>
                <div class="parse-format-chips" aria-label="支持的文件格式">
                  <span class="fmt-chip">PNG</span>
                  <span class="fmt-chip">JPG</span>
                  <span class="fmt-chip">WebP</span>
                  <span class="fmt-chip">BMP</span>
                  <span class="fmt-chip">TIFF</span>
                  <span class="fmt-chip fmt-chip-pdf">PDF</span>
                </div>
              </div>
              <p class="parse-page-note muted">
                PDF 按页解析，页数受账号上限约束；可在下方滑动条指定本次解析页数。
                <span v-if="pdfPageCountLoading" style="color: #e6a23c; font-weight: 500;">（正在读取 PDF 页数…）</span>
              </p>
              <details class="parse-page-details">
                <summary>输出文件说明</summary>
                <ul class="parse-page-details-list">
                  <li>多页 PDF 的可视化结果为 <strong>ZIP</strong>；单图或单页为 <strong>PNG</strong>。</li>
                  <li>
                    文本：<code>*_raw.mmd</code> 为模型直出；<code>*.mmd</code> 为经
                    <code>qwenvl_cast_html_tag</code> 转换后的结果。
                  </li>
                </ul>
              </details>
            </div>

            <div class="upload-area" :class="{ dragover: dragOver }" tabindex="0" role="button"
              @click="fileInput?.click()" @dragenter.prevent="dragOver = true" @dragover.prevent="dragOver = true"
              @dragleave.prevent="dragOver = false" @drop.prevent="onDrop">
              <input
                ref="fileInput"
                type="file"
                class="hidden-file"
                multiple
                accept=".png,.jpg,.jpeg,.bmp,.tiff,.webp,.pdf,image/*,application/pdf"
                @change="onFilePick"
              />
              <div class="upload-icon" aria-hidden="true">📄</div>
              <div class="upload-hint">将文件拖到此处，或 <em>点击选择</em>（可多选，可多次添加）</div>
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
                  <span v-if="isPdfFileName(q.file.name)" class="parse-queue-pdf-meta" :class="{ 'pdf-loading': q.pdfNumPages === undefined, 'pdf-error': q.pdfError }">
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
              <el-input
                v-model="prompt"
                clearable
                placeholder="留空则使用默认：QwenVL HTML"
              />
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
                    <button
                      type="button"
                      class="parse-prompt-pick"
                      @click="setParsePromptExample('请识别图像中的文字与版面结构，输出为 HTML。')"
                    >
                      中文任务说明
                    </button>
                    <span class="muted">用中文明确「识别什么、输出什么」，可在默认效果不理想时尝试。</span>
                  </li>
                </ul>
              </details>
            </label>

            <div v-show="hasQueue" class="field pdf-pages-field">
              <div class="pdf-pages-header">
                <span class="pdf-pages-label">📄 解析页数</span>
                <el-tooltip placement="top" effect="dark">
                  <template #content>
                    <div style="max-width: 320px; line-height: 1.6;">
                      <div style="font-weight: 600; margin-bottom: 8px;">💡 使用说明</div>
                      <div>• 滑动条最大值 = min(您的上限, 队列总页数)</div>
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
                    <el-input-number
                      v-model="pdfPagesRequested"
                      class="pdf-pages-input-num"
                      :min="1"
                      :max="pdfPagesSliderMax"
                      :step="1"
                      :precision="0"
                      :disabled="!hasQueue || parsing"
                      controls-position="right"
                      @change="clampPdfPagesRequested"
                    />
                    <span class="pdf-pages-current-unit">页</span>
                    <span v-if="queueTotalPages != null" class="pdf-pages-total-badge">
                      共 {{ queueTotalPages }} 页
                    </span>
                    <span v-else-if="pdfPageCountLoading" class="pdf-pages-loading-badge">
                      <span class="loading-dots">读取中</span>
                    </span>
                  </div>
                  <el-slider
                    v-model="pdfPagesRequested"
                    class="pdf-pages-slider-el"
                    :min="1"
                    :max="pdfPagesSliderMax"
                    :step="1"
                    :disabled="!hasQueue || parsing"
                    :format-tooltip="formatPdfPagesTooltip"
                    :show-tooltip="true"
                  />
                </div>
                <div class="pdf-pages-slider-feet">
                  <span class="pdf-pages-range-min">1</span>
                  <span class="muted pdf-pages-hint">
                    <template v-if="pdfPageCountLoading">⏳ 正在读取 PDF 页数…</template>
                    <template v-else-if="queueTotalPages != null">
                      上限 {{ pdfPagesMax }} 页 · 当前 {{ pdfPagesSliderMax }} 页
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

            <el-alert v-if="parseErr" :title="parseErr" type="error" show-icon :closable="false"
              style="margin-top: 16px" />

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
                    <a
                      v-for="item in batchFileLinks(br.job_id)"
                      :key="item.path"
                      class="file-link"
                      :href="item.path"
                      target="_blank"
                      rel="noopener"
                    >
                      下载 {{ item.name }}
                    </a>
                  </template>
                  <div v-else class="batch-result-err">{{ br.filename }}：{{ br.error }}</div>
                </div>
              </template>
              <template v-else>
                <a
                  v-for="item in resultLinks"
                  :key="item.path"
                  class="file-link"
                  :href="item.path"
                  target="_blank"
                  rel="noopener"
                >
                  下载 {{ item.name }}
                </a>
              </template>
            </div>
          </div>
        </div>

        <!-- 系统设置 -->
        <div v-show="activeMenu === 'settings'" class="view-panel">
          <div class="container card settings-container">
            <div class="settings-header">
              <h1>
                <span class="settings-icon">⚙️</span>
                系统设置
              </h1>
              <p class="lead">
                {{
                  isAdmin
                    ? '下方「当前生效摘要」对所有用户可见；「全局配置」仅管理员可编辑，保存后写入数据库 app_settings。'
                    : '以下为当前对您生效的运行参数（只读）。修改注册策略、路径等需使用管理员账号。'
                }}
              </p>
            </div>

            <el-alert v-if="settingsLoadError" :title="settingsLoadError" type="error" :closable="false"
              style="margin-bottom: 16px" />

            <div class="settings-summary">
              <h3 class="settings-h3">当前生效摘要</h3>
              <el-descriptions :column="1" border size="small" class="settings-desc">
                <el-descriptions-item label="PDF 解析页数上限">
                  <template v-if="settingsSummary.is_admin">
                    <span>无限制</span>
                    <span class="muted">（系统全局上限 {{ settingsSummary.pdf_max_pages_global }}）</span>
                  </template>
                  <template v-else>
                    <span>{{ settingsSummary.pdf_max_pages }}</span>
                    <span class="muted">（系统全局上限 {{ settingsSummary.pdf_max_pages_global }}）</span>
                  </template>
                </el-descriptions-item>
                <el-descriptions-item label="解析输出目录">
                  <span class="path-text">{{ settingsSummary.output_dir }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="模型已加载">
                  <el-tag :type="settingsSummary.model_loaded ? 'success' : 'warning'" size="small">
                    {{ settingsSummary.model_loaded ? '已加载' : '未加载' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="账号权限">
                  {{ settingsSummary.is_admin ? '管理员' : '普通用户' }}
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <div v-if="isAdmin" class="admin-settings">
              <h3 class="settings-h3">全局配置（保存至数据库）</h3>
              <el-alert class="settings-save-hint" type="info" :closable="false" show-icon
                title="修改任意项后请点击「保存到数据库」才会生效；未保存时刷新或重新登录不会看到新配置。可按下方分栏切换，减少单页滚动。" />
              <div class="settings-save-bar">
                <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
                <span class="muted settings-save-bar-tip">所有分栏中的修改一次保存即可写入数据库</span>
              </div>

              <div class="admin-settings-form">
                <el-tabs v-model="adminSettingsTab" type="border-card" class="admin-settings-tabs">
                  <el-tab-pane label="注册与安全" name="security">
                    <!-- 使用手风琴面板按分组折叠，避免 Tooltip 显示问题 -->
                    <el-collapse v-model="activeSecurityPanels" class="settings-accordion">
                      
                      <!-- 基础 -->
                      <el-collapse-item name="basic" title="基础">
                        <div class="accordion-panel-content">
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">允许注册</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，前台将不允许新用户注册（与「注册方式」开关配合）。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.registration_enabled" />
                          </el-form-item>
                        </div>
                      </el-collapse-item>

                      <!-- 图形验证码 -->
                      <el-collapse-item name="captcha" title="图形验证码">
                        <div class="accordion-panel-content">
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">登录页</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">开启后，用户登录前需先完成图形验证码。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.captcha_login_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">注册页（发码前）</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">在点击「获取邮箱/短信验证码」之前需先通过图形验证码。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.captcha_register_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">找回密码页</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">在发送找回验证码之前需先通过图形验证码。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.captcha_forgot_enabled" />
                          </el-form-item>
                        </div>
                      </el-collapse-item>

                      <!-- 注册 / 登录 / 找回 -->
                      <el-collapse-item name="auth_methods" title="注册 / 登录 / 找回">
                        <template #title>
                          <div class="accordion-title">
                            <span>注册 / 登录 / 找回</span>
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">
                                  控制是否可使用邮箱或手机号进行注册、登录与找回。关闭某项后对应入口在前端隐藏。请至少保留一种注册方式与一种登录方式，避免无法登录。
                                </div>
                              </template>
                              <span class="settings-help-trigger settings-help-trigger--title" aria-label="说明">?</span>
                            </el-tooltip>
                          </div>
                        </template>
                        <div class="accordion-panel-content">
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">邮箱注册</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，注册页将隐藏邮箱注册流程。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.register_email_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">手机号注册</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，注册页将隐藏手机号注册流程。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.register_phone_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">用户名或邮箱登录</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，登录页仅允许使用手机号登录（若已开启手机号登录）。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.login_email_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">手机号登录</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，登录页仅允许用户名或邮箱登录。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.login_phone_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">邮箱找回密码</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，找回密码页将隐藏邮箱流程。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.forgot_email_enabled" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">手机号找回密码</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">关闭后，找回密码页将隐藏手机号流程。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.forgot_phone_enabled" />
                          </el-form-item>
                        </div>
                      </el-collapse-item>

                      <!-- 解析限制 -->
                      <el-collapse-item name="parse_limits" title="解析限制">
                        <div class="accordion-panel-content">
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">PDF 最大解析页数</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">单份 PDF 解析时允许的最大页数上限。</div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-input-number v-model="adminForm.pdf_max_pages" :min="1" :max="500" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">显示页码标记</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    开启后，解析结果中会包含页码标记（如 &lt;!-- 第 X 页 --&gt; 和 ## 第 X 页）；关闭后仅输出纯内容。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.show_page_numbers" />
                          </el-form-item>

                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">图片输出模式</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    <div><strong>Base64 嵌入</strong>：图片以 base64 格式嵌入 Markdown，单文件但体积大</div>
                                    <div><strong>独立文件</strong>：图片保存为单独文件，Markdown 引用相对路径，需下载 ZIP</div>
                                    <div><strong>不输出</strong>：不包含任何图片，仅文本内容</div>
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-select v-model="adminForm.image_output_mode" style="width: 200px">
                              <el-option label="Base64 嵌入" value="base64" />
                              <el-option label="独立文件" value="separate" />
                              <el-option label="不输出" value="none" />
                            </el-select>
                          </el-form-item>
                        </div>
                      </el-collapse-item>

                      <!-- 任务管理 -->
                      <el-collapse-item name="task_management" title="任务管理">
                        <div class="accordion-panel-content">
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">僵尸任务超时时长（分钟）</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    超过此时长且仍为“进行中”状态的任务将被视为僵尸任务。系统启动时或管理员手动触发时会自动检测并恢复这些任务。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-input-number v-model="adminForm.stale_job_timeout_minutes" :min="1" :max="1440" />
                          </el-form-item>
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">登录超时时长（分钟）</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    用户无操作超过此时长后，系统将自动退出登录并返回登录页面。默认值为 10 分钟。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-input-number v-model="adminForm.login_timeout_minutes" :min="1" :max="1440" />
                          </el-form-item>
                        </div>
                      </el-collapse-item>

                      <!-- 密码规则 -->
                      <el-collapse-item name="password_rules" title="密码规则">
                        <div class="accordion-panel-content">
                          <el-alert type="info" :closable="false" style="margin-bottom: 16px">
                            <template #default>
                              以下规则将应用于注册、修改密码和找回密码场景
                            </template>
                          </el-alert>
                          
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">最小长度</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    密码的最小字符数要求。默认值为 8 个字符。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-input-number v-model="adminForm.password_min_length" :min="1" :max="128" />
                          </el-form-item>
                          
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">要求大写字母</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    是否要求密码中至少包含一个大写字母（A-Z）。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.password_require_uppercase" />
                          </el-form-item>
                          
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">要求小写字母</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    是否要求密码中至少包含一个小写字母（a-z）。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.password_require_lowercase" />
                          </el-form-item>
                          
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">要求数字</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    是否要求密码中至少包含一个数字（0-9）。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.password_require_digit" />
                          </el-form-item>
                          
                          <el-form-item>
                            <template #label>
                              <span class="settings-label-with-tip">要求特殊字符</span>
                              <el-tooltip placement="top" :show-after="300" effect="dark">
                                <template #content>
                                  <div class="settings-tooltip-block">
                                    是否要求密码中至少包含一个特殊字符，如 !@#$%^&*()_+-=[]{}|;:,.<>?/~` 等。
                                  </div>
                                </template>
                                <span class="settings-help-trigger" aria-label="说明">?</span>
                              </el-tooltip>
                            </template>
                            <el-switch v-model="adminForm.password_require_special" />
                          </el-form-item>
                        </div>
                      </el-collapse-item>

                    </el-collapse>
                  </el-tab-pane>

                  <el-tab-pane label="路径与模型" name="paths">
                    <el-form label-position="top" class="settings-panel-form settings-panel-form--paths">
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            解析输出目录
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">
                                  须为运行后端服务所在主机上的绝对路径。留空则使用环境变量 OUTPUT_DIR / PARSE_OUTPUT_DIR 或默认 out/。示例：Linux/macOS：
                                  /var/logics/out；Windows：C:\Data\logics-out 或
                                  C:/Data/logics-out。「选择文件夹」因浏览器限制通常无法自动填入服务器路径，请在资源管理器地址栏复制绝对路径后粘贴。
                                </div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.output_dir" type="textarea" :rows="2" spellcheck="false"
                          autocomplete="off" placeholder="例如 /var/logics/out 或 C:\Data\logics-out" />
                        <div class="path-actions">
                          <el-tooltip v-if="!dirPickerSupported" placement="top"
                            content="当前浏览器不支持系统文件夹选择。请手动输入或从资源管理器复制路径。">
                            <span class="path-btn-wrap">
                              <el-button disabled>选择本地文件夹…</el-button>
                            </span>
                          </el-tooltip>
                          <el-button v-else type="default" @click="pickOutputDir">选择本地文件夹…</el-button>
                          <el-button type="default" @click="pasteOutputPathFromClipboard">从剪贴板粘贴</el-button>
                        </div>
                        <p v-if="effectivePaths.output" class="form-hint muted">当前实际生效：{{ effectivePaths.output }}</p>
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            模型本地目录
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">
                                  <strong>支持两种路径格式：</strong><br><br>
                                  <strong>1. 绝对路径</strong>（推荐）<br>
                                  例如：<code>/home/user/models/Logics-Parsing-v2</code><br>
                                  或 Windows：<code>D:\models\Logics-Parsing-v2</code><br><br>
                                  <strong>2. 相对路径</strong><br>
                                  相对于项目根目录下的 <code>logics-parsingv2/</code> 文件夹<br>
                                  例如：<code>weights/Logics-Parsing-v2</code><br>
                                  实际路径为：<code>./logics-parsingv2/weights/Logics-Parsing-v2</code><br><br>
                                  💡 留空则使用环境变量 MODEL_PATH 或项目默认权重目录
                                </div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.model_local_path" type="textarea" :rows="2"
                          placeholder="例如：weights/Logics-Parsing-v2 或 /absolute/path/to/model" />
                        <p class="form-hint muted" style="margin-top: 4px; font-size: 12px;">
                          💡 支持绝对路径（如 <code>/home/user/models</code>）或相对路径（相对于 <code>logics-parsingv2/</code> 文件夹）
                        </p>
                        <p v-if="effectivePaths.model" class="form-hint muted">当前实际生效：{{ effectivePaths.model }}</p>
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            HuggingFace 仓库 ID
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">后台「下载模型」选择 HuggingFace 时使用的默认仓库 ID。</div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.hf_repo_id" />
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            ModelScope 仓库 ID
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">后台「下载模型」选择 ModelScope 时使用的默认仓库 ID。</div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.ms_repo_id" />
                      </el-form-item>

                      <el-divider content-position="left">模型下载与加载</el-divider>
                      
                      <!-- 模型状态提示 -->
                      <el-alert 
                        v-if="modelStatus.model_loaded" 
                        title="✅ 模型已加载" 
                        type="success" 
                        :closable="false"
                        style="margin-bottom: 12px"
                      >
                        <template #default>
                          模型已就绪，可以开始解析文档
                        </template>
                      </el-alert>
                      <el-alert 
                        v-else-if="!modelStatus.model_loaded && !modelStatus.downloading && !modelStatus.download_message" 
                        title="⚠️ 模型未加载" 
                        type="warning" 
                        :closable="false"
                        style="margin-bottom: 12px"
                      >
                        <template #default>
                          请下载模型后点击「重新加载模型」
                        </template>
                      </el-alert>
                      
                      <p class="settings-inline-hint muted">
                        与项目 download_model_v2 一致
                        <el-tooltip placement="top" :show-after="300" effect="dark">
                          <template #content>
                            <div class="settings-tooltip-block">从所选源下载权重到上方「模型本地目录」；完成后可点「重新加载模型」。</div>
                          </template>
                          <span class="settings-help-trigger" aria-label="说明">?</span>
                        </el-tooltip>
                      </p>
                      <el-radio-group v-model="dlSource" class="settings-dl-source" :disabled="modelStatus.downloading">
                        <el-radio-button value="modelscope">ModelScope</el-radio-button>
                        <el-radio-button value="huggingface">HuggingFace</el-radio-button>
                      </el-radio-group>
                      <div class="btn-row btn-row-split">
                        <el-button 
                          :loading="dlLoading || modelStatus.downloading" 
                          :disabled="modelStatus.downloading"
                          @click="runModelDownload"
                        >
                          {{ modelStatus.downloading ? '下载中...' : '后台下载到模型目录' }}
                        </el-button>
                        <div style="display: flex; align-items: center; gap: 8px;">
                          <el-button 
                            type="primary" 
                            :loading="reloadLoading" 
                            :disabled="modelStatus.downloading"
                            @click="reloadModel"
                          >
                            重新加载模型
                          </el-button>
                          <span v-if="reloadError" class="reload-error-text">{{ reloadError }}</span>
                        </div>
                      </div>
                      
                      <!-- 下载日志区域 -->
                      <div v-if="modelStatus.download_message" class="download-log-section">
                        <div class="log-header">
                          <span class="log-title">📋 下载日志</span>
                          <el-tag 
                            :type="modelStatus.downloading ? 'warning' : (modelStatus.download_success ? 'success' : 'danger')" 
                            size="small"
                          >
                            {{ modelStatus.downloading ? '进行中' : (modelStatus.download_success ? '已完成' : '失败') }}
                          </el-tag>
                        </div>
                        <div class="log-content">
                          <pre class="log-text">{{ modelStatus.download_message }}</pre>
                        </div>
                        <div v-if="modelStatus.downloading && modelStatus.download_dest" class="log-footer">
                          <div class="status-row">
                            <span class="status-label">来源：</span>
                            <span class="status-value">{{ modelStatus.download_source || '-' }}</span>
                          </div>
                          <div class="status-row">
                            <span class="status-label">仓库：</span>
                            <span class="status-value">{{ modelStatus.download_repo || '-' }}</span>
                          </div>
                          <div class="status-row">
                            <span class="status-label">目标：</span>
                            <span class="status-value status-path">{{ modelStatus.download_dest }}</span>
                          </div>
                        </div>
                      </div>
                    </el-form>
                  </el-tab-pane>

                  <el-tab-pane label="邮件 SMTP" name="email">
                    <el-form label-position="top" class="settings-panel-form settings-panel-form--switch"
                      @submit.prevent>
                      <el-form-item class="settings-form-item-switch">
                        <template #label>
                          <span class="settings-label-with-tip">仅模拟</span>
                          <el-tooltip placement="top" :show-after="300" effect="dark">
                            <template #content>
                              <div class="settings-tooltip-block">
                                开启时仅在服务端控制台打印邮件内容，不真实发信。正式环境请关闭并填写下方 SMTP。
                              </div>
                            </template>
                            <span class="settings-help-trigger" aria-label="说明">?</span>
                          </el-tooltip>
                        </template>
                        <el-switch v-model="adminForm.email_mock" />
                      </el-form-item>
                      <el-form-item label="SMTP 主机">
                        <el-input v-model="adminForm.smtp_host" placeholder="如 smtp.qq.com" clearable />
                      </el-form-item>
                      <el-form-item label="端口">
                        <el-input-number v-model="adminForm.smtp_port" :min="1" :max="65535" />
                      </el-form-item>
                      <el-form-item label="用户名">
                        <el-input v-model="adminForm.smtp_user" autocomplete="off" clearable />
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">发件人地址</span>
                        </template>
                        <el-input v-model="adminForm.smtp_from" placeholder="可空，默认与用户名相同" clearable />
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            密码或授权码
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">仅存数据库；留空表示不修改已保存的密码。授权码常见于邮箱 SMTP。</div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.smtp_password" type="password" show-password
                          autocomplete="new-password" placeholder="留空不修改已保存" />
                        <p v-if="adminForm.smtp_password_configured" class="form-hint muted">已在库中保存密码</p>
                      </el-form-item>
                      <el-form-item class="settings-form-item-switch">
                        <template #label>
                          <span class="settings-label-with-tip">STARTTLS</span>
                          <el-tooltip placement="top" :show-after="300" effect="dark">
                            <template #content>
                              <div class="settings-tooltip-block">常见与 587 端口配合使用。</div>
                            </template>
                            <span class="settings-help-trigger" aria-label="说明">?</span>
                          </el-tooltip>
                        </template>
                        <el-switch v-model="adminForm.smtp_use_tls" />
                      </el-form-item>
                    </el-form>
                  </el-tab-pane>

                  <el-tab-pane label="短信 HTTP" name="sms">
                    <el-form label-position="top" class="settings-panel-form settings-panel-form--switch"
                      @submit.prevent>
                      <el-form-item class="settings-form-item-switch">
                        <template #label>
                          <span class="settings-label-with-tip">仅模拟</span>
                          <el-tooltip placement="top" :show-after="300" effect="dark">
                            <template #content>
                              <div class="settings-tooltip-block">开启时仅在控制台打印验证码，不真实发短信。正式环境请关闭并填写回调 URL。</div>
                            </template>
                            <span class="settings-help-trigger" aria-label="说明">?</span>
                          </el-tooltip>
                        </template>
                        <el-switch v-model="adminForm.sms_mock" />
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            回调 URL
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">
                                  关闭模拟后，将向该地址 POST JSON，默认包含 phone、code、purpose（register / forgot）。可通过下方模板自定义。
                                </div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.sms_http_url" placeholder="https://your-sms-provider.com/send"
                          clearable />
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            密钥
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">可选；若填写，请求将带头 X-Sms-Secret。留空不修改已保存密钥。</div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.sms_http_secret" type="password" show-password
                          autocomplete="new-password" placeholder="留空不修改已保存" />
                        <p v-if="adminForm.sms_http_secret_configured" class="form-hint muted">已在库中保存密钥</p>
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            额外请求头（JSON）
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">合并进 HTTP 请求头，例如 Authorization。</div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.sms_http_headers_json" type="textarea" :rows="2"
                          placeholder='例如 {"Authorization":"Bearer xxx"}' />
                      </el-form-item>
                      <el-form-item>
                        <template #label>
                          <span class="settings-label-row">
                            请求体模板
                            <el-tooltip placement="top" :show-after="300" effect="dark">
                              <template #content>
                                <div class="settings-tooltip-block">
                                  默认 JSON；可使用占位符 phone、code、purpose。需为合法 JSON 字符串以便解析后发送。
                                </div>
                              </template>
                              <span class="settings-help-trigger" aria-label="说明">?</span>
                            </el-tooltip>
                          </span>
                        </template>
                        <el-input v-model="adminForm.sms_http_body_template" type="textarea" :rows="3"
                          placeholder='默认：{"phone":"{phone}","code":"{code}","purpose":"{purpose}"}' />
                      </el-form-item>
                    </el-form>
                  </el-tab-pane>
                </el-tabs>

                <div class="settings-save-bar settings-save-bar--bottom">
                  <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
                  <span class="muted settings-save-bar-tip">与顶部按钮相同，保存全部配置</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 个人中心 -->
        <div v-show="activeMenu === 'profile'" class="view-panel">
          <div class="container card profile-container">
            <div class="page-header">
              <h1>
                <span class="page-icon">👤</span>
                个人中心
              </h1>
            </div>
            
            <!-- 基本信息卡片 -->
            <div class="profile-section">
              <h3 class="profile-section-title">📋 基本信息</h3>
              <el-descriptions :column="1" border size="default" class="profile-info">
                <el-descriptions-item label="用户名">
                  <strong>{{ userProfile.username }}</strong>
                </el-descriptions-item>
                <el-descriptions-item label="邮箱">
                  {{ userProfile.email || '—' }}
                </el-descriptions-item>
                <el-descriptions-item label="手机号">
                  {{ userProfile.phone || '未绑定' }}
                </el-descriptions-item>
                <el-descriptions-item label="注册时间">
                  {{ fmtTime(userProfile.created_at) }}
                </el-descriptions-item>
                <el-descriptions-item label="账号状态">
                  <el-tag :type="userProfile.is_active ? 'success' : 'danger'" size="small">
                    {{ userProfile.is_active ? '正常' : '已禁用' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="角色权限">
                  <el-tag :type="userProfile.is_admin ? 'warning' : 'info'" size="small">
                    {{ userProfile.is_admin ? '管理员' : '普通用户' }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <!-- 使用配额卡片 -->
            <div class="profile-section">
              <h3 class="profile-section-title">📊 使用配额</h3>
              <el-descriptions :column="1" border size="default" class="profile-quota">
                <el-descriptions-item label="PDF 解析页数上限">
                  <template v-if="userProfile.is_admin">
                    <el-tag type="success" size="small">无限制</el-tag>
                    <span class="muted" style="margin-left: 8px;">（管理员特权）</span>
                  </template>
                  <template v-else>
                    <strong style="font-size: 1.1em; color: var(--accent);">{{ userProfile.pdf_max_pages_effective }}</strong>
                    <span class="muted" style="margin-left: 8px;">页</span>
                    <div v-if="!userProfile.pdf_use_default" class="quota-detail muted">
                      个人设置：{{ userProfile.pdf_max_pages_personal }} 页 | 系统全局：{{ userProfile.pdf_max_pages_global }} 页
                    </div>
                    <div v-else class="quota-detail muted">
                      使用系统全局默认值：{{ userProfile.pdf_max_pages_global }} 页
                    </div>
                  </template>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <!-- 输出配置卡片 -->
            <div class="profile-section">
              <h3 class="profile-section-title">⚙️ 输出配置</h3>
              <el-descriptions :column="1" border size="default" class="profile-config">
                <el-descriptions-item label="图片下载权限">
                  <el-tag :type="userProfile.can_download_images ? 'success' : 'info'" size="small">
                    {{ userProfile.can_download_images ? '允许' : '禁止' }}
                  </el-tag>
                  <span class="muted" style="margin-left: 8px;">（仅当输出模式为 separate 时生效）</span>
                </el-descriptions-item>
                <el-descriptions-item label="图片输出模式">
                  <template v-if="userProfile.image_output_use_default">
                    <el-tag type="info" size="small">跟随系统设置</el-tag>
                    <span class="muted" style="margin-left: 8px;">当前系统默认为 base64 嵌入模式</span>
                  </template>
                  <template v-else>
                    <el-tag type="primary" size="small">{{ userProfile.image_output_mode }}</el-tag>
                    <div class="quota-detail muted">
                      <span v-if="userProfile.image_output_mode === 'base64'">图片以 Base64 编码嵌入 Markdown</span>
                      <span v-else-if="userProfile.image_output_mode === 'separate'">图片保存为独立文件</span>
                      <span v-else-if="userProfile.image_output_mode === 'none'">不输出图片</span>
                    </div>
                  </template>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <!-- 快捷操作 -->
            <div class="profile-section">
              <h3 class="profile-section-title">🔧 快捷操作</h3>
              <div class="profile-actions">
                <el-button @click="activeMenu = 'records'">查看生成记录</el-button>
                <el-button @click="activeMenu = 'cache'">清理缓存</el-button>
                <el-button type="primary" plain @click="refreshProfile">🔄 刷新信息</el-button>
              </div>
            </div>

            <!-- 密码修改 -->
            <div class="profile-section">
              <h3 class="profile-section-title">🔑 密码修改</h3>
              <el-alert v-if="pwErr" :title="pwErr" type="error" :closable="false" style="margin-bottom: 12px" />
              <el-alert v-if="pwOk" title="密码已更新" type="success" :closable="false" style="margin-bottom: 12px" />
              <el-form label-width="120px" size="default">
                <el-form-item label="当前密码">
                  <el-input v-model="pw.old" type="password" show-password placeholder="请输入当前密码" style="max-width: 400px" />
                </el-form-item>
                <el-form-item label="新密码">
                  <el-input v-model="pw.n1" type="password" show-password placeholder="至少 8 位字符" style="max-width: 400px" />
                </el-form-item>
                <el-form-item label="确认新密码">
                  <el-input v-model="pw.n2" type="password" show-password placeholder="再次输入新密码" style="max-width: 400px" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="pwLoading" @click="changePassword">保存新密码</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>

        <!-- 生成记录 -->
        <div v-show="activeMenu === 'records'" class="view-panel">
          <div class="container card records-container">
            <div class="page-header">
              <h1>
                <span class="page-icon">📋</span>
                生成记录
              </h1>
            </div>
            <p class="lead">
              {{
                isAdmin
                  ? '管理员可查询、删除全部用户的任务。'
                  : '仅可查询、删除当前账号自己的任务。'
              }}
              进行中的任务需先停止再删除；删除将移除记录与磁盘输出目录。缓存已清除的条目无法下载。
              <span class="muted" style="display: inline-block; margin-top: 8px; font-size: 0.9em;">💡 提示：在小屏幕上可左右滑动表格查看所有字段。</span>
            </p>
            <div class="records-toolbar">
              <el-date-picker v-model="recordsDateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
                end-placeholder="结束日期" value-format="YYYY-MM-DD" style="max-width: 320px" />
              <el-input v-model="recordsFilename" clearable placeholder="文件名包含" style="max-width: 200px"
                @keyup.enter="searchRecords" />
              <el-button type="primary" @click="searchRecords">查询</el-button>
              <el-button class="btn-ghost btn-sm" @click="loadRecords">刷新</el-button>
              <el-button v-if="isAdmin" type="warning" plain :loading="recoveringStaleJobs"
                @click="confirmRecoverStaleJobs">
                🔄 恢复僵尸任务
              </el-button>
              <el-button 
                type="success" 
                plain 
                :disabled="!recordsSelection.length || batchDownloading"
                :loading="batchDownloading" 
                @click="handleBatchDownload"
              >
                📦 批量下载 ({{ recordsSelection.length }})
              </el-button>
              <el-button type="danger" plain :disabled="!recordsSelection.length || batchDeleting"
                :loading="batchDeleting" @click="confirmBatchDeleteJobs">
                批量删除 ({{ recordsSelection.length }})
              </el-button>
            </div>
            <div class="table-wrap">
              <el-table ref="recordsTableRef" v-loading="recordsLoading" :data="records" row-key="job_id" stripe
                style="width: 100%" @selection-change="(rows) => (recordsSelection = rows)">
                <el-table-column type="selection" width="48" :selectable="recordsRowSelectable"
                  :reserve-selection="true" />
                <el-table-column v-if="isAdmin" prop="username" label="用户" min-width="100" show-overflow-tooltip />
                <el-table-column prop="created_at" label="创建时间" min-width="150">
                  <template #default="{ row }">
                    {{ fmtTime(row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column prop="original_filename" label="文件" min-width="200" show-overflow-tooltip />
                <el-table-column label="解析页数" min-width="90" align="center">
                  <template #default="{ row }">
                    <span v-if="row.pages_parsed != null">{{ row.pages_parsed }}</span>
                    <span v-else class="muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="状态" min-width="90">
                  <template #default="{ row }">
                    {{ statusLabel(row.status) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="操作"
                  min-width="280"
                  fixed="right"
                  align="right"
                  header-align="right"
                  class-name="records-actions-col"
                >
                  <template #default="{ row }">
                    <div class="records-actions-cell">
                      <template v-if="row.can_download">
                        <a class="table-link" :href="dl(row.job_id, 'visualization')" target="_blank"
                          rel="noopener">可视化</a>
                        <a class="table-link" :href="dl(row.job_id, 'raw')" target="_blank" rel="noopener">raw</a>
                        <a class="table-link" :href="dl(row.job_id, 'markdown')" target="_blank" rel="noopener">mmd</a>
                      </template>
                      <span v-else-if="row.cache_cleared" class="muted">缓存已清除</span>
                      <span v-else-if="row.status === 'processing'" class="muted">进行中</span>
                      <span v-else class="muted">无文件</span>
                      <el-button v-if="row.status !== 'processing'" link type="danger"
                        :loading="deletingJobId === row.job_id" class="records-actions-del" @click="confirmDeleteJob(row)">
                        删除
                      </el-button>
                      <span v-else class="muted records-actions-del-hint">先停止后可删</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="records-pagination">
              <el-pagination v-model:current-page="recordsPage" v-model:page-size="recordsPageSize"
                :total="recordsTotal" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next"
                @current-change="loadRecords" @size-change="loadRecords" />
            </div>
          </div>
        </div>

        <!-- 缓存清除 -->
        <div v-show="activeMenu === 'cache'" class="view-panel">
          <div class="container card cache-container">
            <div class="page-header">
              <h1>
                <span class="page-icon">🗑️</span>
                缓存清除
              </h1>
            </div>
            <div class="parse-page-intro">
              <p class="parse-page-lead">
                勾选下方列表中的任务，删除其在磁盘上的解析输出目录以释放空间。生成记录仍保留，但清除后将无法再次下载该任务的文件。
              </p>
              <div class="parse-formats">
                <span class="parse-formats-label">可清理</span>
                <div class="parse-format-chips" aria-label="可清理的任务类型">
                  <span class="fmt-chip">已完成</span>
                  <span class="fmt-chip">已停止</span>
                  <span class="fmt-chip fmt-chip-cache-fail">失败残留</span>
                </div>
              </div>
              <p class="parse-page-note muted">
                进行中的任务请先在「文档解析」中停止；若只需删记录、不删磁盘，请使用「生成记录」。
              </p>
              <details class="parse-page-details">
                <summary>详细说明</summary>
                <ul class="parse-page-details-list">
                  <li>
                    此处仅列出后端标记为<strong>可清除</strong>的已结束任务（成功、已停止或符合策略的失败项等）。
                  </li>
                  <li>
                    当前版本在推理<strong>失败</strong>后通常会<strong>自动删除</strong>该任务目录；若升级服务前仍有残留，可在此勾选清除。
                  </li>
                </ul>
              </details>
            </div>
            <div id="cache-toolbar">
              <el-button class="btn-ghost btn-sm" @click="loadCacheList">刷新列表</el-button>
              <el-button class="btn-danger-outline" :disabled="!cacheSelection.length"
                @click="clearCache">清除选中缓存</el-button>
            </div>
            <div class="table-wrap">
              <el-table v-loading="cacheLoading" :data="cacheRows" row-key="job_id" stripe style="width: 100%"
                @selection-change="(rows) => (cacheSelection = rows)">
                <el-table-column type="selection" width="48" />
                <el-table-column label="完成时间" min-width="150">
                  <template #default="{ row }">
                    {{ fmtTime(row.completed_at || row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column prop="original_filename" label="文件" min-width="200" show-overflow-tooltip />
                <el-table-column label="状态" min-width="90">
                  <template #default="{ row }">
                    {{ statusLabel(row.status) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>

        <!-- 用户管理（仅管理员） -->
        <div v-show="activeMenu === 'users' && isAdmin" class="view-panel">
          <div class="container card users-container">
            <div class="page-header">
              <h1>
                <span class="page-icon">👥</span>
                用户管理
              </h1>
            </div>
            <p class="lead">
              搜索用户名或邮箱；可修改普通用户的启用状态、角色与密码。表格中不可勾选管理员账号，故批量操作仅针对普通用户。批量设置解析页数、批量删除前均会弹出警告或确认。删除用户将同时删除其解析任务记录且不可恢复。
            </p>
            <div class="records-toolbar">
              <el-input v-model="userSearchQ" clearable placeholder="用户名 / 邮箱" style="max-width: 280px"
                @keyup.enter="searchUsers" />
              <el-button type="primary" @click="searchUsers">查询</el-button>
              <el-button class="btn-ghost btn-sm" @click="loadUsers">刷新</el-button>
              <el-button type="success" @click="openCreateUserDialog">➕ 添加用户</el-button>
              <el-button :disabled="!usersSelection.length || usersBatchLoading" :loading="usersBatchLoading"
                @click="batchUsersActive(true)">
                批量启用 ({{ usersSelection.length }})
              </el-button>
              <el-button type="warning" plain :disabled="!usersSelection.length || usersBatchLoading"
                :loading="usersBatchLoading" @click="batchUsersActive(false)">
                批量禁用
              </el-button>
              <el-button type="warning" plain :disabled="!usersSelection.length || usersBatchLoading"
                :loading="usersBatchLoading" @click="batchUsersAdmin(true)">
                批量设为管理员
              </el-button>
              <el-button plain :disabled="!usersSelection.length || usersBatchLoading" :loading="usersBatchLoading"
                @click="batchUsersAdmin(false)">
                批量取消管理员
              </el-button>
              <el-button type="primary" plain :disabled="!usersSelection.length || usersBatchLoading"
                :loading="usersBatchLoading" @click="openBatchPdfDialog">
                批量设置解析页数上限
              </el-button>
              <el-button type="danger" plain :disabled="!usersSelection.length || usersBatchLoading"
                :loading="usersBatchLoading" @click="batchUsersDelete">
                批量删除用户
              </el-button>
            </div>
            <div class="table-wrap">
              <el-table ref="usersTableRef" v-loading="usersLoading" :data="usersList" row-key="id" stripe
                style="width: 100%" @selection-change="(rows) => (usersSelection = rows)">
                <el-table-column type="selection" width="48" :selectable="usersRowSelectable"
                  :reserve-selection="true" />
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="username" label="用户名" min-width="120" />
                <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
                <el-table-column prop="phone" label="手机号" min-width="140" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-if="row.phone" class="muted">{{ row.phone }}</span>
                    <span v-else class="muted" style="opacity: 0.5;">未绑定</span>
                  </template>
                </el-table-column>
                <el-table-column label="管理员" width="90">
                  <template #default="{ row }">
                    <el-tag :type="row.is_admin ? 'warning' : 'info'" size="small">{{ row.is_admin ? '是' : '否'
                      }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="90">
                  <template #default="{ row }">
                    <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '正常' : '禁用'
                      }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="注册时间" min-width="160">
                  <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
                </el-table-column>
                <el-table-column label="可解析页数" min-width="160" align="center">
                  <template #default="{ row }">
                    <template v-if="row.is_admin">
                      <span class="muted">无限制</span>
                    </template>
                    <template v-else>
                      <span>系统限制页数（{{ userPdfEffectiveDisplay(row) }}）</span>
                      <div v-if="row.pdf_max_pages != null" class="muted user-pdf-raw-hint">个人配置 {{ row.pdf_max_pages }}</div>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column label="图片输出模式" min-width="140" align="center">
                  <template #default="{ row }">
                    <template v-if="row.image_output_mode == null">
                      <el-tag type="info" size="small">跟随系统</el-tag>
                    </template>
                    <template v-else-if="row.image_output_mode === 'base64'">
                      <el-tag type="primary" size="small">Base64 嵌入</el-tag>
                    </template>
                    <template v-else-if="row.image_output_mode === 'separate'">
                      <el-tag type="success" size="small">独立文件</el-tag>
                    </template>
                    <template v-else-if="row.image_output_mode === 'none'">
                      <el-tag type="warning" size="small">不输出</el-tag>
                    </template>
                    <template v-else>
                      <span class="muted">{{ row.image_output_mode }}</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="200" fixed="right">
                  <template #default="{ row }">
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                      <el-button 
                        v-if="!row.is_admin || row.username === username"
                        link 
                        type="primary" 
                        size="small"
                        @click="openUserEdit(row)"
                      >
                        编辑
                      </el-button>
                      <el-button 
                        link 
                        type="warning" 
                        size="small"
                        @click="viewUserSession(row)"
                      >
                        查看会话
                      </el-button>
                      <el-button 
                        v-if="row.id !== currentUserId && row.has_session"
                        link 
                        type="danger" 
                        size="small"
                        @click="kickUserConfirm(row)"
                      >
                        踢出
                      </el-button>
                      <span v-else-if="row.id === currentUserId" class="muted" style="font-size: 12px;">不可操作</span>
                      <span v-else class="muted" style="font-size: 12px;">未登录</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="users-pagination">
              <el-pagination v-model:current-page="userPage" v-model:page-size="userPageSize" :total="userTotal"
                :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadUsers"
                @size-change="loadUsers" />
            </div>
          </div>
        </div>

        <el-dialog v-model="userEditVisible" title="编辑用户" width="520px" destroy-on-close @closed="resetUserEditForm">
          <el-form label-position="top">
            <el-form-item label="用户名">
              <el-input :model-value="userEditForm.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input :model-value="userEditForm.email" disabled />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input :model-value="userEditForm.phone || '未绑定'" disabled />
            </el-form-item>
            <el-form-item label="管理员">
              <el-switch v-model="userEditForm.is_admin" :disabled="userEditForm.is_self" />
            </el-form-item>
            <el-form-item label="账号启用">
              <el-switch v-model="userEditForm.is_active" :disabled="userEditForm.is_self" />
            </el-form-item>
            <el-form-item label="新密码（留空则不修改）">
              <el-input v-model="userEditForm.new_password" type="password" show-password autocomplete="new-password"
                placeholder="至少 8 位" />
            </el-form-item>
            <el-form-item label="PDF 解析页数上限">
              <div class="user-pdf-limit-row">
                <el-checkbox v-model="userEditForm.pdf_use_default">与系统全局一致</el-checkbox>
              </div>
              <el-input-number v-show="!userEditForm.pdf_use_default" v-model="userEditForm.pdf_max_pages" :min="1"
                :max="10000" :disabled="userEditForm.pdf_use_default" controls-position="right" style="width: 100%" />
              <p v-show="!userEditForm.pdf_use_default" class="muted user-pdf-limit-note">
                实际生效为 min(系统全局上限, 此处值)。管理员账号解析不受个人配额限制。
              </p>
            </el-form-item>
            <el-form-item label="图片输出模式">
              <div class="user-pdf-limit-row">
                <el-checkbox v-model="userEditForm.image_output_use_default">跟随系统设置</el-checkbox>
              </div>
              <el-select
                v-show="!userEditForm.image_output_use_default"
                v-model="userEditForm.image_output_mode"
                :disabled="userEditForm.image_output_use_default"
                style="width: 100%; margin-top: 8px"
              >
                <el-option label="Base64 嵌入" value="base64" />
                <el-option label="独立文件" value="separate" />
                <el-option label="不输出" value="none" />
              </el-select>
              <p v-show="!userEditForm.image_output_use_default" class="muted user-pdf-limit-note">
                留空则使用系统全局配置。仅当选择「独立文件」时，需配合「可下载图片」权限。
              </p>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="userEditVisible = false">取消</el-button>
            <el-button type="primary" :loading="userSaveLoading" @click="submitUserEdit">
              保存
            </el-button>
          </template>
        </el-dialog>

        <el-dialog v-model="createUserVisible" title="添加新用户" width="520px" destroy-on-close @closed="resetCreateUserForm">
          <el-form ref="createUserFormRef" :model="createUserForm" label-position="top" :rules="createUserRules">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="createUserForm.username" placeholder="3-50 个字符" autocomplete="username" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="createUserForm.email" placeholder="example@domain.com" autocomplete="email" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="createUserForm.password" type="password" show-password autocomplete="new-password"
                placeholder="至少 8 位" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="createUserForm.confirmPassword" type="password" show-password autocomplete="new-password"
                placeholder="再次输入密码" />
            </el-form-item>
            <el-form-item label="管理员">
              <el-switch v-model="createUserForm.is_admin" />
              <span class="muted" style="margin-left: 8px; font-size: 12px;">管理员不受 PDF 页数限制</span>
            </el-form-item>
            <el-form-item label="账号启用">
              <el-switch v-model="createUserForm.is_active" />
            </el-form-item>
            <el-form-item label="PDF 解析页数上限">
              <div class="user-pdf-limit-row">
                <el-checkbox v-model="createUserForm.pdf_use_default">与系统全局一致</el-checkbox>
              </div>
              <el-input-number v-show="!createUserForm.pdf_use_default" v-model="createUserForm.pdf_max_pages" :min="1"
                :max="10000" :disabled="createUserForm.pdf_use_default" controls-position="right" style="width: 100%" />
              <p v-show="!createUserForm.pdf_use_default" class="muted user-pdf-limit-note">
                实际生效为 min(系统全局上限, 此处值)。
              </p>
            </el-form-item>
            <el-form-item label="图片输出模式">
              <div class="user-pdf-limit-row">
                <el-checkbox v-model="createUserForm.image_output_use_default">跟随系统设置</el-checkbox>
              </div>
              <el-select
                v-show="!createUserForm.image_output_use_default"
                v-model="createUserForm.image_output_mode"
                :disabled="createUserForm.image_output_use_default"
                style="width: 100%; margin-top: 8px"
              >
                <el-option label="Base64 嵌入" value="base64" />
                <el-option label="独立文件" value="separate" />
                <el-option label="不输出" value="none" />
              </el-select>
              <p v-show="!createUserForm.image_output_use_default" class="muted user-pdf-limit-note">
                留空则使用系统全局配置。
              </p>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="createUserVisible = false">取消</el-button>
            <el-button type="primary" :loading="createUserLoading" @click="submitCreateUser">
              创建
            </el-button>
          </template>
        </el-dialog>

        <el-dialog v-model="batchPdfDialogVisible" title="批量设置 PDF 解析页数上限" width="480px" destroy-on-close>
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            class="mb-3"
            title="将写入选中用户的个人上限；「与系统全局一致」表示清除个人覆盖，实际配额仍受系统全局上限约束。"
          />
          <el-form label-position="top">
            <el-form-item label="与系统全局一致（清除个人上限）">
              <el-switch v-model="batchPdfUseDefault" />
            </el-form-item>
            <el-form-item v-if="!batchPdfUseDefault" label="个人上限（页）">
              <el-input-number v-model="batchPdfPages" :min="1" :max="10000" controls-position="right" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="batchPdfDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="usersBatchLoading" @click="submitBatchPdf">提交</el-button>
          </template>
        </el-dialog>

        <!-- 查看用户会话对话框 -->
        <el-dialog v-model="sessionDialogVisible" title="用户会话信息" width="600px" destroy-on-close>
          <div v-if="sessionLoading" class="text-center py-4">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <p class="mt-2">加载中...</p>
          </div>
          <div v-else-if="!sessionData.has_session" class="text-center py-4">
            <el-icon :size="48" color="#909399"><CircleClose /></el-icon>
            <p class="mt-2 muted">该用户当前没有活跃会话</p>
          </div>
          <div v-else>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="用户名">
                {{ sessionData.session.username }}
              </el-descriptions-item>
              <el-descriptions-item label="登录 IP">
                {{ sessionData.session.ip_address || '未知' }}
              </el-descriptions-item>
              <el-descriptions-item label="浏览器">
                <span style="font-size: 12px; word-break: break-all;">
                  {{ sessionData.session.user_agent || '未知' }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="登录时间">
                {{ fmtTime(sessionData.session.login_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="最后活跃">
                {{ fmtTime(sessionData.session.last_active) }}
              </el-descriptions-item>
            </el-descriptions>
            <el-alert
              type="info"
              :closable="false"
              show-icon
              class="mt-3"
              title="提示：踢出用户后，该用户的 Token 将立即失效，需要重新登录。"
            />
          </div>
          <template #footer>
            <el-button @click="sessionDialogVisible = false">关闭</el-button>
            <el-button 
              v-if="sessionData.has_session && sessionUserId !== currentUserId"
              type="danger" 
              :loading="kickingUser"
              @click="confirmKickUser"
            >
              踢出该用户
            </el-button>
          </template>
        </el-dialog>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, toRaw, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as pdfjsLib from 'pdfjs-dist'
import http from '@/api/http'
import { startTokenRefresh, stopTokenRefresh } from '@/api/http'

// 使用 cdn 或本地 worker
if (typeof window !== 'undefined') {
  // Docker 环境中优先使用 CDN，避免 worker 路径问题
  const cdnUrls = [
    `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`,
    `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`,
    `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`
  ]
  
  // 首先尝试使用 CDN（更可靠）
  pdfjsLib.GlobalWorkerOptions.workerSrc = cdnUrls[0]
  console.log('[PDF] 使用 CDN worker:', cdnUrls[0])
  
  // 可选：如果 CDN 失败，再尝试本地 worker
  // try {
  //   const workerUrl = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).href
  //   pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl
  //   console.log('[PDF] workerSrc 已设置:', workerUrl)
  // } catch (err) {
  //   console.warn('[PDF] 本地 worker 加载失败，使用 CDN', err)
  //   pdfjsLib.GlobalWorkerOptions.workerSrc = cdnUrls[0]
  // }
}

/** 模板与逻辑共用：判断是否为 PDF 扩展名（const 保证在 script setup 中稳定暴露给模板） */
const isPdfFileName = (name) => /\.pdf$/i.test(String(name || ''))

/** 生成 UUID v4（兼容不支持 crypto.randomUUID 的环境） */
function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // 降级方案：使用 Math.random 生成 UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

const PDF_PAGES_DEFAULT = 5

const router = useRouter()
const username = ref('…')
/** 当前用户 ID */
const currentUserId = ref(null)
/** 用户详细信息 */
const userProfile = reactive({
  id: null,
  username: '',
  email: '',
  phone: '',
  is_admin: false,
  is_active: true,
  created_at: null,
  // PDF 配额
  pdf_max_pages_global: 80,
  pdf_max_pages_personal: null,
  pdf_max_pages_effective: 80,
  pdf_use_default: true,
  // 图片输出配置
  can_download_images: true,
  image_output_mode: null,
  image_output_use_default: true,
})
/** 视口 ≤768px 时使用抽屉侧栏 */
const isMobile = ref(false)
const mobileNavOpen = ref(false)
const activeMenu = ref('parse')
const fileInput = ref(null)
const dragOver = ref(false)
/** 待解析队列：解析前可增删；开始后顺序执行 */
const parseQueue = ref([])
const parseBatchResults = ref([])
const batchAbort = ref(false)
/** 留空则上传时不带 prompt 字段，后端使用默认「QwenVL HTML」 */
const prompt = ref('')
/** PDF 本次解析页数：默认 5，且 ≤ min(账号上限, 队列中 PDF 最大页数)（若已解析出页数） */
const pdfPagesRequested = ref(PDF_PAGES_DEFAULT)
const parsing = ref(false)
const progressPct = ref(0)
const progressMsg = ref('')
const parseErr = ref('')
const showProgress = ref(false)
const showResult = ref(false)
const resultPartial = ref(false)
const currentJobId = ref(null)
/** 本轮解析完成后的 job_id，用于下载链接（currentJobId 在完成后会清空） */
const resultJobId = ref(null)
let ws = null

const showStop = computed(() => parsing.value && !!currentJobId.value)

const settingsLoadError = ref('')
const settingsSummary = reactive({
  pdf_max_pages: 80,
  pdf_max_pages_global: 80,
  model_loaded: false,
  output_dir: '',
  is_admin: false,
})

const pdfPagesMax = computed(() => Math.max(1, settingsSummary.pdf_max_pages || 80))
const hasQueue = computed(() => parseQueue.value.length > 0)

/**
 * 队列「合计页数」：每个图片计 1 页；PDF 用本地读取的实际页数。
 * 任一 PDF 仍在读取或读取失败导致无法计入时返回 null。
 */
function queueItemPageContribution(x) {
  if (!isPdfFileName(x.file.name)) return { ready: true, n: 1 }
  if (x.pdfNumPages === undefined) return { ready: false }
  if (typeof x.pdfNumPages === 'number' && x.pdfNumPages > 0) return { ready: true, n: x.pdfNumPages }
  return { ready: false }
}

const queueTotalPages = computed(() => {
  let sum = 0
  for (const x of parseQueue.value) {
    const c = queueItemPageContribution(x)
    if (!c.ready) return null
    sum += c.n
  }
  return sum
})

/**
 * 滑块 / 数字框的 max：min(当前用户 PDF 页数上限, 队列文档总页数)。
 * 总页数 = 各 PDF 实际页数之和 + 每张图片计 1 页；尚有 PDF 未读出页数时无法合计，max 暂等于用户上限。
 */
const pdfPagesSliderMax = computed(() => {
  const userCap = pdfPagesMax.value
  const total = queueTotalPages.value
  if (total != null && total > 0) return Math.min(userCap, total)
  return userCap
})

const pdfPageCountLoading = computed(() =>
  parseQueue.value.some((x) => isPdfFileName(x.file.name) && x.pdfNumPages === undefined),
)

function clampPdfPagesRequested() {
  const m = pdfPagesSliderMax.value
  let v = pdfPagesRequested.value
  if (typeof v !== 'number' || Number.isNaN(v)) v = PDF_PAGES_DEFAULT
  v = Math.round(v)
  pdfPagesRequested.value = Math.min(Math.max(1, v), m)
}

function setParsePromptExample(text) {
  prompt.value = text
}

function formatPdfPagesTooltip(val) {
  return `${val} 页`
}

async function loadPdfNumPagesForQueueItem(item) {
  if (!/\.pdf$/i.test(item.file.name)) return
  
  console.log(`[PDF] 开始读取页数: ${item.file.name}, 大小: ${item.file.size} bytes`)
  
  let retryCount = 0
  const maxRetries = 2
  
  while (retryCount <= maxRetries) {
    try {
      const buf = await item.file.arrayBuffer()
      
      // 验证文件是否为有效的 PDF
      if (buf.byteLength < 5) {
        throw new Error('文件太小，不是有效的 PDF')
      }
      
      console.log(`[PDF] 尝试加载 PDF.js, workerSrc: ${pdfjsLib.GlobalWorkerOptions.workerSrc}`)
      
      const doc = await pdfjsLib.getDocument({ 
        data: buf,
        // 禁用 CMap 加载以加快速度
        cMapUrl: undefined,
        cMapPacked: false,
        // 禁用字体加载
        disableFontFace: true,
        // 减少内存使用
        maxImageSize: -1,
      }).promise
      
      const numPages = doc.numPages
      
      // 关键：通过替换数组元素来触发 Vue 响应式更新
      const index = parseQueue.value.findIndex(x => x.id === item.id)
      if (index !== -1) {
        parseQueue.value[index] = { ...parseQueue.value[index], pdfNumPages: numPages }
      }
      
      console.log(`[PDF页数] ${item.file.name}: ${numPages} 页`)
      return // 成功则退出
      
    } catch (err) {
      retryCount++
      console.warn(`[PDF页数读取尝试 ${retryCount}/${maxRetries + 1}] ${item.file.name}:`, err.message)
      console.error('[PDF] 详细错误:', err)
      
      // 如果是最后一次尝试，标记为失败
      if (retryCount > maxRetries) {
        console.error(`[PDF页数读取最终失败] ${item.file.name}:`, err)
        
        // 提供更友好的错误信息
        let errorMsg = '无法读取'
        if (err.message.includes('worker') || err.message.includes('Worker')) {
          errorMsg = '浏览器不支持'
        } else if (err.message.includes('Invalid') || err.message.includes('损坏')) {
          errorMsg = '格式无效'
        } else if (err.message.includes('Network') || err.message.includes('network')) {
          errorMsg = '网络错误'
        }
        
        // 失败时也更新为 null
        const index = parseQueue.value.findIndex(x => x.id === item.id)
        if (index !== -1) {
          parseQueue.value[index] = { 
            ...parseQueue.value[index], 
            pdfNumPages: null,
            pdfError: errorMsg
          }
        }
      }
      
      // 短暂延迟后重试
      if (retryCount <= maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 500))
      }
    }
  }
  
  clampPdfPagesRequested()
}

/** 上传时：不超过账号上限、不超过当前输入，且不超过该 PDF 实际页数（若已知） */
function effectivePdfPagesForItem(item) {
  const cap = pdfPagesMax.value
  const want = Math.min(cap, Math.max(1, Math.round(Number(pdfPagesRequested.value) || PDF_PAGES_DEFAULT)))
  if (!/\.pdf$/i.test(item.file.name)) return want
  const doc = item.pdfNumPages
  if (typeof doc === 'number' && doc > 0) return Math.min(want, doc)
  return want
}

const fileLabel = computed(() => {
  const q = parseQueue.value
  if (!q.length) return '尚未添加文件，点击上方区域或拖拽添加（可多选、可多次添加）'
  const kb = Math.round(q.reduce((s, x) => s + x.file.size, 0) / 1024)
  return `已添加 ${q.length} 个文件（合计约 ${kb} KB），解析前可移除单项或清空`
})

const PARSE_ALLOWED_EXT = new Set(['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.pdf'])

/** 注入全局 Tooltip 样式，覆盖 Element Plus 默认白色背景 */
function injectTooltipStyles() {
  const styleId = 'custom-tooltip-styles'
  // 避免重复注入
  if (document.getElementById(styleId)) return
  
  const style = document.createElement('style')
  style.id = styleId
  style.textContent = `
    /* 强制覆盖所有 dark 主题的 Tooltip */
    .el-popper.is-dark,
    .el-tooltip__popper.is-dark {
      background: linear-gradient(135deg, #1a2540 0%, #141c2f 100%) !important;
      border: 1px solid rgba(99, 102, 241, 0.3) !important;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 
                  0 0 0 1px rgba(99, 102, 241, 0.1),
                  inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
      color: #e8eef8 !important;
      backdrop-filter: blur(8px);
      z-index: 9999 !important;
    }
    
    .el-popper.is-dark .el-popper__arrow::before,
    .el-tooltip__popper.is-dark .el-popper__arrow::before {
      background: linear-gradient(135deg, #1a2540 0%, #141c2f 100%) !important;
      border: 1px solid rgba(99, 102, 241, 0.3) !important;
    }
    
    .el-popper.is-dark .el-popper__content,
    .el-tooltip__popper.is-dark .el-popper__content {
      color: #e8eef8 !important;
      line-height: 1.6;
      padding: 2px 0;
    }
    
    .el-popper.is-dark code,
    .el-tooltip__popper.is-dark code {
      background: rgba(0, 0, 0, 0.35) !important;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
      color: #7dd3fc !important;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      border: 1px solid rgba(125, 211, 252, 0.2);
    }
  `
  document.head.appendChild(style)
  console.log('[Tooltip Styles] Custom dark theme injected')
}

function parseFileExt(name) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

/** 与待解析队列内「同一本地文件」的弱指纹（同路径再次选择通常 name/size/lastModified 一致） */
function parseQueueFileKey(f) {
  return `${f.name}\0${f.size}\0${f.lastModified}`
}

function addFilesToQueue(fileList) {
  const arr = Array.from(fileList || []).filter((f) => f && PARSE_ALLOWED_EXT.has(parseFileExt(f.name)))
  if (!arr.length) {
    if (fileList && fileList.length) ElMessage.warning('没有可添加的文件（仅支持图片或 PDF）')
    return
  }
  const existing = new Set(parseQueue.value.map((x) => parseQueueFileKey(x.file)))
  const seenThisPick = new Set()
  const newFiles = []
  let skipped = 0
  for (const f of arr) {
    const k = parseQueueFileKey(f)
    if (existing.has(k) || seenThisPick.has(k)) {
      skipped += 1
      continue
    }
    seenThisPick.add(k)
    existing.add(k)
    newFiles.push(f)
  }
  if (!newFiles.length) {
    ElMessage.warning(skipped ? '所选文件均已在待解析列表中，未重复添加' : '')
    return
  }
  if (skipped) {
    ElMessage.info(`已跳过 ${skipped} 个重复项（与列表中或本次选择重复）`)
  }
  const added = newFiles.map((file) => {
    const row = { id: generateUUID(), file }
    if (/\.pdf$/i.test(file.name)) {
      row.pdfNumPages = undefined
      loadPdfNumPagesForQueueItem(row)
    }
    return row
  })
  parseQueue.value = [...parseQueue.value, ...added]
  parseErr.value = ''
  showResult.value = false
  showProgress.value = false
  clampPdfPagesRequested()
}

function removeQueueItem(id) {
  parseQueue.value = parseQueue.value.filter((x) => x.id !== id)
}

function clearParseQueue() {
  parseQueue.value = []
}
const effectivePaths = reactive({
  output: '',
  model: '',
})
const isAdmin = ref(false)
const adminSaveLoading = ref(false)
/** 系统设置分栏：security | paths | email | sms */
const adminSettingsTab = ref('security')
/** 注册与安全板块的手风琴展开状态 */
const activeSecurityPanels = ref([])
/** 邮件 SMTP 板块的手风琴展开状态 */
const activeEmailPanels = ref([])
/** 短信 HTTP 板块的手风琴展开状态 */
const activeSmsPanels = ref([])
const dlLoading = ref(false)
const reloadLoading = ref(false)
const reloadError = ref('')  // 重新加载错误信息
const dlSource = ref('modelscope')
const modelStatus = ref({
  model_loaded: false,
  downloading: false,
  download_success: false,
  download_error: null,
  download_message: '',
})
let statusCheckInterval = null
const adminForm = reactive({
  registration_enabled: true,
  captcha_login_enabled: false,
  captcha_register_enabled: false,
  captcha_forgot_enabled: false,
  pdf_max_pages: 80,
  output_dir: '',
  model_local_path: '',
  hf_repo_id: '',
  ms_repo_id: '',
  email_mock: true,
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_from: '',
  smtp_password: '',
  smtp_use_tls: true,
  smtp_password_configured: false,
  register_email_enabled: true,
  register_phone_enabled: true,
  login_email_enabled: true,
  login_phone_enabled: true,
  forgot_email_enabled: true,
  forgot_phone_enabled: true,
  sms_mock: true,
  sms_http_url: '',
  sms_http_secret: '',
  sms_http_headers_json: '',
  sms_http_body_template: '',
  sms_http_secret_configured: false,
  show_page_numbers: true,
  image_output_mode: 'base64',
  stale_job_timeout_minutes: 10,  // 僵尸任务超时时长（分钟）
  login_timeout_minutes: 10,  // 登录超时时长（分钟）
  // 密码规则
  password_min_length: 8,
  password_require_uppercase: true,
  password_require_lowercase: true,
  password_require_digit: true,
  password_require_special: false,
})

/** Chromium 等支持 File System Access API；Firefox/Safari 通常无 showDirectoryPicker */
const dirPickerSupported = computed(
  () => typeof window !== 'undefined' && typeof window.showDirectoryPicker === 'function',
)

const pw = reactive({ old: '', n1: '', n2: '' })
const pwErr = ref('')
const pwOk = ref(false)
const pwLoading = ref(false)

const records = ref([])
const recordsLoading = ref(false)
const recordsPage = ref(1)
const recordsPageSize = ref(20)
const recordsTotal = ref(0)
const recordsDateRange = ref(null)
const recordsFilename = ref('')
const recordsTableRef = ref(null)
const recordsSelection = ref([])
const batchDeleting = ref(false)
const batchDownloading = ref(false)  // 批量下载加载状态
const recoveringStaleJobs = ref(false)  // 恢复僵尸任务加载状态

const usersTableRef = ref(null)
const usersSelection = ref([])
const usersBatchLoading = ref(false)
const batchPdfDialogVisible = ref(false)
const batchPdfUseDefault = ref(true)
const batchPdfPages = ref(80)
const deletingJobId = ref(null)

const usersList = ref([])
/** 与本次用户列表一并返回的系统全局 PDF 页数上限，用于表格展示与回退 */
const usersPdfGlobalCap = ref(80)
const usersLoading = ref(false)
const userPage = ref(1)
const userPageSize = ref(20)
const userTotal = ref(0)
const userSearchQ = ref('')
const userEditVisible = ref(false)
const userSaveLoading = ref(false)
const userEditForm = reactive({
  id: null,
  username: '',
  email: '',
  phone: '',
  is_admin: false,
  is_active: true,
  is_self: false,
  /** 正在编辑另一名管理员：仅可查看，不可改状态与密码 */
  is_target_other_admin: false,
  new_password: '',
  pdf_max_pages: 80,
  pdf_use_default: true,
  image_output_mode: null, // null 表示跟随系统设置
  image_output_use_default: true,
})

// 会话管理相关
const sessionDialogVisible = ref(false)
const sessionLoading = ref(false)
const sessionData = reactive({
  has_session: false,
  session: null,
})
const sessionUserId = ref(null)
const kickingUser = ref(false)

// 创建用户相关
const createUserVisible = ref(false)
const createUserLoading = ref(false)
const createUserFormRef = ref(null)
const createUserForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  is_admin: false,
  is_active: true,
  pdf_max_pages: 80,
  pdf_use_default: true,
  image_output_mode: null, // null 表示跟随系统设置
  image_output_use_default: true,
})

const validatePass2 = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== createUserForm.password) {
    callback(new Error('两次输入密码不一致!'))
  } else {
    callback()
  }
}

const createUserRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, validator: validatePass2, trigger: 'blur' },
  ],
}

const cacheRows = ref([])
const cacheLoading = ref(false)
const cacheSelection = ref([])

const menuTitle = computed(() => {
  const map = {
    parse: '文档解析',
    settings: '系统设置',
    profile: '个人中心',
    records: '生成记录',
    cache: '缓存清除',
    users: '用户管理',
  }
  return map[activeMenu.value] || ''
})

const resultLinks = computed(() => {
  const id = resultJobId.value
  if (!id) return []
  return batchFileLinks(id)
})

function batchFileLinks(jobId) {
  if (!jobId) return []
  const links = [
    { name: '可视化（单页 PNG / 多页 ZIP）', path: `/download/${jobId}/visualization` },
    { name: '原始输出 _raw.mmd', path: `/download/${jobId}/raw` },
    { name: '转换输出 .mmd', path: `/download/${jobId}/markdown` },
    { name: '完整结果（ZIP，含图片）', path: `/download/${jobId}/result` },
  ]
  return links
}

function dl(jobId, type) {
  return `/download/${jobId}/${type}`
}

function fmtTime(s) {
  if (!s) return ''
  return String(s).replace('T', ' ').replace('Z', '')
}

function statusLabel(s) {
  const map = { processing: '进行中', completed: '已完成', stopped: '已停止', failed: '失败' }
  return map[s] || s
}

/** 管理员账号不参与批量启用/禁用/改角色 */
function usersRowSelectable(row) {
  return !row.is_admin
}

function recordsRowSelectable(row) {
  return row.status !== 'processing'
}

function onMenuSelect(index) {
  activeMenu.value = index
  if (isMobile.value) mobileNavOpen.value = false
}

function onSiderBrandClick() {
  if (isMobile.value) mobileNavOpen.value = false
}

function updateMobileLayout() {
  const mq = window.matchMedia('(max-width: 768px)')
  isMobile.value = mq.matches
  if (!mq.matches) mobileNavOpen.value = false
}

watch([pdfPagesMax, pdfPagesSliderMax], () => {
  clampPdfPagesRequested()
})

watch(activeMenu, (m) => {
  if (m === 'settings') loadSettings()
  if (m === 'records') loadRecords()
  if (m === 'cache') loadCacheList()
  if (m === 'users' && isAdmin.value) loadUsers()
})

watch([mobileNavOpen, isMobile], () => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = isMobile.value && mobileNavOpen.value ? 'hidden' : ''
})

onMounted(async () => {
  // 注入全局 Tooltip 样式（确保覆盖 Element Plus 默认白色背景）
  injectTooltipStyles()
  
  updateMobileLayout()
  window.addEventListener('resize', updateMobileLayout, { passive: true })
  window.addEventListener('keydown', onNavEscape)
  const mq = window.matchMedia('(max-width: 768px)')
  if (mq.addEventListener) {
    mq.addEventListener('change', updateMobileLayout)
  } else {
    mq.addListener(updateMobileLayout)
  }
  try {
    const { data } = await http.get('/api/auth/me')
    username.value = data?.username || '用户'
    isAdmin.value = !!data?.is_admin
    currentUserId.value = data?.id || null
    
    // 更新用户详细信息
    Object.assign(userProfile, {
      id: data.id,
      username: data.username,
      email: data.email,
      phone: data.phone || '',
      is_admin: !!data.is_admin,
      is_active: !!data.is_active,
      created_at: data.created_at,
      pdf_max_pages_global: data.pdf_max_pages_global || 80,
      pdf_max_pages_personal: data.pdf_max_pages_personal,
      pdf_max_pages_effective: data.pdf_max_pages_effective || 80,
      pdf_use_default: !!data.pdf_use_default,
      can_download_images: !!data.can_download_images,
      image_output_mode: data.image_output_mode || null,
      image_output_use_default: !!data.image_output_use_default,
    })
    
    // 普通用户不能访问系统设置页面
    if (!isAdmin.value && activeMenu.value === 'settings') {
      activeMenu.value = 'parse'
    }
    
    await loadSettings()
    await checkModelStatus()  // 加载模型状态
    
    // 启动 Token 自动刷新机制（防止页面刷新后定时器丢失）
    startTokenRefresh()
    console.log('[Workspace] Token 刷新机制已启动')
  } catch {
    router.replace('/login')
  }
})

function onNavEscape(e) {
  if (e.key === 'Escape' && mobileNavOpen.value) mobileNavOpen.value = false
}

onUnmounted(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
  window.removeEventListener('resize', updateMobileLayout)
  window.removeEventListener('keydown', onNavEscape)
  const mq = window.matchMedia('(max-width: 768px)')
  if (mq.removeEventListener) {
    mq.removeEventListener('change', updateMobileLayout)
  } else {
    mq.removeListener(updateMobileLayout)
  }
  // 清理模型状态检查定时器
  stopStatusChecking()
  // 停止 Token 刷新机制
  stopTokenRefresh()
})

async function logout() {
  // 停止 Token 刷新机制
  stopTokenRefresh()
  console.log('[退出] Token 刷新机制已停止')
  
  await http.post('/api/auth/logout')
  router.replace('/')
}

function onFilePick(e) {
  addFilesToQueue(e.target.files)
  if (fileInput.value) fileInput.value.value = ''
}

function onDrop(e) {
  dragOver.value = false
  addFilesToQueue(e.dataTransfer.files)
  if (fileInput.value) fileInput.value.value = ''
}

async function pickOutputDir() {
  if (typeof window.showDirectoryPicker !== 'function') return
  try {
    const dir = await window.showDirectoryPicker()
    ElMessage({
      message: `已选择文件夹「${dir.name}」。因浏览器安全限制，无法自动填入完整磁盘路径。若该目录在运行后端的机器上，请在该机资源管理器地址栏或终端中复制其绝对路径，粘贴到上方输入框。`,
      type: 'info',
      duration: 12000,
      showClose: true,
    })
  } catch (e) {
    if (e?.name === 'AbortError') return
    ElMessage.error(e?.message || '无法打开文件夹选择')
  }
}

async function pasteOutputPathFromClipboard() {
  try {
    if (!navigator.clipboard || typeof navigator.clipboard.readText !== 'function') {
      ElMessage.warning('当前环境无法读取剪贴板，请直接在输入框中 Ctrl+V 粘贴')
      return
    }
    const t = (await navigator.clipboard.readText()).trim()
    if (!t) {
      ElMessage.warning('剪贴板为空')
      return
    }
    adminForm.output_dir = t
    ElMessage.success('已粘贴到输出目录')
  } catch {
    ElMessage.error('读取剪贴板失败（需 HTTPS 或 localhost，且需浏览器授权）')
  }
}

async function loadSettings() {
  settingsLoadError.value = ''
  try {
    const { data } = await http.get('/api/settings')
    settingsSummary.pdf_max_pages = data.pdf_max_pages ?? 80
    settingsSummary.pdf_max_pages_global = data.pdf_max_pages_global ?? data.pdf_max_pages ?? 80
    settingsSummary.model_loaded = !!data.model_loaded
    settingsSummary.output_dir = data.output_dir || '—'
    settingsSummary.is_admin = !!data.is_admin

    effectivePaths.output = ''
    effectivePaths.model = ''
    if (data.is_admin && data.admin) {
      const a = data.admin
      adminForm.registration_enabled = a.registration_enabled !== false
      adminForm.captcha_login_enabled = !!a.captcha_login_enabled
      adminForm.captcha_register_enabled = !!a.captcha_register_enabled
      adminForm.captcha_forgot_enabled = !!a.captcha_forgot_enabled
      adminForm.pdf_max_pages = a.pdf_max_pages || 80
      adminForm.output_dir = a.output_dir ?? ''
      adminForm.model_local_path = a.model_local_path ?? ''
      adminForm.hf_repo_id = a.hf_repo_id || ''
      adminForm.ms_repo_id = a.ms_repo_id || ''
      adminForm.email_mock = a.email_mock !== false
      adminForm.smtp_host = a.smtp_host ?? ''
      adminForm.smtp_port = a.smtp_port ?? 587
      adminForm.smtp_user = a.smtp_user ?? ''
      adminForm.smtp_from = a.smtp_from ?? ''
      adminForm.smtp_password = ''
      adminForm.smtp_use_tls = a.smtp_use_tls !== false
      adminForm.smtp_password_configured = !!a.smtp_password_configured
      adminForm.register_email_enabled = a.register_email_enabled !== false
      adminForm.register_phone_enabled = a.register_phone_enabled !== false
      adminForm.login_email_enabled = a.login_email_enabled !== false
      adminForm.login_phone_enabled = a.login_phone_enabled !== false
      adminForm.forgot_email_enabled = a.forgot_email_enabled !== false
      adminForm.forgot_phone_enabled = a.forgot_phone_enabled !== false
      adminForm.sms_mock = a.sms_mock !== false
      adminForm.sms_http_url = a.sms_http_url ?? ''
      adminForm.sms_http_secret = ''
      adminForm.sms_http_headers_json = a.sms_http_headers_json ?? ''
      adminForm.sms_http_body_template = a.sms_http_body_template ?? ''
      adminForm.sms_http_secret_configured = !!a.sms_http_secret_configured
      adminForm.show_page_numbers = a.show_page_numbers !== false
      adminForm.image_output_mode = a.image_output_mode || 'base64'
      adminForm.stale_job_timeout_minutes = a.stale_job_timeout_minutes ?? 10
      adminForm.login_timeout_minutes = a.login_timeout_minutes ?? 10
      // 密码规则
      adminForm.password_min_length = a.password_min_length ?? 8
      adminForm.password_require_uppercase = a.password_require_uppercase !== false
      adminForm.password_require_lowercase = a.password_require_lowercase !== false
      adminForm.password_require_digit = a.password_require_digit !== false
      adminForm.password_require_special = !!a.password_require_special
      effectivePaths.output = a.effective_output_dir || ''
      effectivePaths.model = a.effective_model_path || ''
    }
  } catch (e) {
    settingsLoadError.value = e.response?.data?.detail || e.message || '加载失败'
  }
}

async function saveAdminSettings() {
  adminSaveLoading.value = true
  try {
    const raw = toRaw(adminForm)
    const payload = { ...raw }
    delete payload.smtp_password_configured
    delete payload.sms_http_secret_configured
    if (!payload.smtp_password || !String(payload.smtp_password).trim()) {
      delete payload.smtp_password
    }
    if (!payload.sms_http_secret || !String(payload.sms_http_secret).trim()) {
      delete payload.sms_http_secret
    }
    await http.put('/api/admin/settings', payload)
    await loadSettings()
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message)
  } finally {
    adminSaveLoading.value = false
  }
}

async function runModelDownload() {
  // 检查是否已有下载任务
  if (modelStatus.value.downloading) {
    ElMessage.warning('已有下载任务正在进行中，请稍后再试')
    return
  }
  
  dlLoading.value = true
  try {
    const { data } = await http.post('/api/admin/model/download', { source: dlSource.value })
    
    // 简洁提示，不显示冗长的消息
    ElMessage({
      message: '✅ 下载任务已启动，请在下方查看实时日志',
      type: 'success',
      duration: 3000,
    })
    
    // 开始定期检查下载状态
    startStatusChecking()
    
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message)
  } finally {
    dlLoading.value = false
  }
}

function startStatusChecking() {
  // 清除之前的定时器
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
  }
  
  // 每 5 秒检查一次状态
  statusCheckInterval = setInterval(async () => {
    await checkModelStatus()
    
    // 如果下载完成或失败，停止检查
    if (!modelStatus.value.downloading) {
      stopStatusChecking()
      
      // 如果下载成功，显示简短通知
      if (modelStatus.value.download_success) {
        ElNotification({
          title: modelStatus.value.model_loaded ? '✅ 模型就绪' : '⚠️ 下载完成',
          message: modelStatus.value.model_loaded 
            ? '模型已成功下载并加载，可以开始使用'
            : '模型已下载，但加载失败，请查看下方日志',
          type: modelStatus.value.model_loaded ? 'success' : 'warning',
          duration: 5000,
        })
      }
      
      // 如果下载失败，显示错误通知
      if (modelStatus.value.download_error) {
        ElNotification({
          title: '❌ 下载失败',
          message: '请查看下方日志了解详细错误信息',
          type: 'error',
          duration: 5000,
        })
      }
    }
  }, 5000)
}

function stopStatusChecking() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
    statusCheckInterval = null
  }
}

async function checkModelStatus() {
  try {
    const { data } = await http.get('/api/admin/model/status')
    modelStatus.value = {
      model_loaded: data.model_loaded,
      downloading: data.downloading,
      download_success: data.download_success,
      download_error: data.download_error,
      download_message: data.download_message,
    }
  } catch (e) {
    console.error('Failed to check model status:', e)
  }
}

async function reloadModel() {
  // 检查是否正在下载
  if (modelStatus.value.downloading) {
    ElMessage.warning('下载任务正在进行中，请等待下载完成后再尝试重新加载')
    return
  }
  
  reloadLoading.value = true
  reloadError.value = ''  // 清除之前的错误
  try {
    const { data } = await http.post('/api/admin/model/reload')
    
    if (data.model_loaded) {
      reloadError.value = ''
      ElMessage.success('✅ 模型已成功重新加载')
    } else {
      reloadError.value = '⚠️ 模型未加载'
      ElMessage.warning(data.message || '模型目录不存在或加载失败')
    }
    
    // 更新状态
    await checkModelStatus()
    await loadSettings()
    
  } catch (e) {
    const errorMsg = e.response?.data?.detail || e.message
    // 提取简短错误信息
    const shortMsg = errorMsg.includes('No such file') ? '模型文件不存在' : 
                     errorMsg.includes('CUDA out of memory') ? '显存不足' :
                     errorMsg.split('：').pop()?.slice(0, 50) || '加载失败'
    reloadError.value = `❌ ${shortMsg}`
    ElMessage.error(`重新加载失败：${shortMsg}`)
  } finally {
    reloadLoading.value = false
  }
}

async function changePassword() {
  pwErr.value = ''
  pwOk.value = false
  if (pw.n1.length < 8) {
    pwErr.value = '新密码至少 8 位'
    return
  }
  if (pw.n1 !== pw.n2) {
    pwErr.value = '两次新密码不一致'
    return
  }
  pwLoading.value = true
  try {
    await http.post('/api/auth/change-password', { old_password: pw.old, new_password: pw.n1 })
    pwOk.value = true
    pw.old = ''
    pw.n1 = ''
    pw.n2 = ''
  } catch (e) {
    pwErr.value = e.response?.data?.detail || e.message
  } finally {
    pwLoading.value = false
  }
}

/** 刷新个人中心信息 */
async function refreshProfile() {
  try {
    const { data } = await http.get('/api/auth/me')
    
    // 更新用户详细信息
    Object.assign(userProfile, {
      id: data.id,
      username: data.username,
      email: data.email,
      phone: data.phone || '',
      is_admin: !!data.is_admin,
      is_active: !!data.is_active,
      created_at: data.created_at,
      pdf_max_pages_global: data.pdf_max_pages_global || 80,
      pdf_max_pages_personal: data.pdf_max_pages_personal,
      pdf_max_pages_effective: data.pdf_max_pages_effective || 80,
      pdf_use_default: !!data.pdf_use_default,
      can_download_images: !!data.can_download_images,
      image_output_mode: data.image_output_mode || null,
      image_output_use_default: !!data.image_output_use_default,
    })
    
    ElMessage.success('个人信息已刷新')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '获取用户信息失败')
  }
}

function formatDateParam(d) {
  if (!d) return null
  if (typeof d === 'string') return d.slice(0, 10)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function searchRecords() {
  recordsPage.value = 1
  recordsSelection.value = []
  recordsTableRef.value?.clearSelection?.()
  loadRecords()
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const params = {
      page: recordsPage.value,
      page_size: recordsPageSize.value,
    }
    if (recordsDateRange.value && recordsDateRange.value.length === 2) {
      const [a, b] = recordsDateRange.value
      params.date_from = typeof a === 'string' ? a : formatDateParam(a)
      params.date_to = typeof b === 'string' ? b : formatDateParam(b)
    }
    if (recordsFilename.value.trim()) params.filename = recordsFilename.value.trim()
    const { data } = await http.get('/api/jobs', { params })
    records.value = data.jobs || []
    recordsTotal.value = data.total ?? 0
  } catch {
    records.value = []
    recordsTotal.value = 0
  } finally {
    recordsLoading.value = false
  }
}

async function confirmDeleteJob(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除任务「${row.original_filename || row.job_id}」吗？将删除数据库记录与输出目录，不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingJobId.value = row.job_id
  try {
    await http.delete(`/api/jobs/${encodeURIComponent(row.job_id)}`)
    ElMessage.success('已删除')
    await loadRecords()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '删除失败')
  } finally {
    deletingJobId.value = null
  }
}

async function confirmBatchDeleteJobs() {
  const rows = recordsSelection.value.filter((r) => r.status !== 'processing')
  if (!rows.length) {
    ElMessage.warning('请选择可删除的任务（进行中的任务不可选，需先停止）')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定批量删除 ${rows.length} 条任务吗？将删除数据库记录与对应输出目录，不可恢复。进行中的任务已自动排除。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const { data } = await http.post('/api/jobs/batch-delete', {
      job_ids: rows.map((r) => r.job_id),
    })
    const n = (data.deleted && data.deleted.length) || 0
    const failed = data.failed || []
    if (failed.length) {
      ElMessage.warning(`已删除 ${n} 条；${failed.length} 条未删除（可能进行中或无权）`)
    } else {
      ElMessage.success(`已删除 ${n} 条`)
    }
    recordsSelection.value = []
    recordsTableRef.value?.clearSelection?.()
    await loadRecords()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

/**
 * 批量下载选中的任务结果
 */
async function handleBatchDownload() {
  // 筛选出已完成且缓存未清除的任务
  const rows = recordsSelection.value.filter((r) => 
    r.status === 'completed' && !r.cache_cleared && r.can_download
  )
  
  if (!rows.length) {
    ElMessage.warning('请选择已完成且缓存未清除的任务')
    return
  }
  
  batchDownloading.value = true
  
  try {
    const jobIds = rows.map((r) => r.job_id)
    
    // 使用 POST 请求获取 ZIP 文件
    const response = await http.post('/api/jobs/batch-download', 
      { job_ids: jobIds },
      { responseType: 'blob' }
    )
    
    // 创建下载链接
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 生成文件名（带时间戳）
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
    link.download = `DocuLogic_批量下载_${timestamp}.zip`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success(`已开始下载 ${rows.length} 个任务的解析结果`)
  } catch (e) {
    console.error('批量下载失败:', e)
    const errorMsg = e.response?.data?.detail || e.message || '批量下载失败'
    ElMessage.error(errorMsg)
  } finally {
    batchDownloading.value = false
  }
}

async function confirmRecoverStaleJobs() {
  try {
    await ElMessageBox.confirm(
      `将检测并恢复所有超过 ${adminForm.stale_job_timeout_minutes} 分钟仍处于“进行中”状态的僵尸任务。这些任务将被标记为“失败”，并清理对应的磁盘文件。是否继续？`,
      '恢复僵尸任务',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  
  recoveringStaleJobs.value = true
  try {
    const { data } = await http.post('/api/admin/recover-stale-jobs', {
      max_stale_minutes: adminForm.stale_job_timeout_minutes,  // 使用系统设置的值
    })
    ElMessage.success(data.message || `已恢复 ${data.recovered_count} 个僵尸任务`)
    await loadRecords()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '恢复失败')
  } finally {
    recoveringStaleJobs.value = false
  }
}

function searchUsers() {
  userPage.value = 1
  usersSelection.value = []
  usersTableRef.value?.clearSelection?.()
  loadUsers()
}

function userPdfEffectiveDisplay(row) {
  const eff = row.pdf_effective_max_pages
  if (eff != null && eff !== '') return Math.max(1, Number(eff))
  const g = usersPdfGlobalCap.value
  if (g != null && g !== '') return Math.max(1, Number(g))
  const fb = settingsSummary.pdf_max_pages_global ?? settingsSummary.pdf_max_pages
  return Math.max(1, Number(fb) || 80)
}

async function loadUsers() {
  if (!isAdmin.value) return
  usersLoading.value = true
  try {
    // 并行加载用户列表和在线用户
    const [usersRes, onlineRes] = await Promise.all([
      http.get('/api/admin/users', {
        params: {
          page: userPage.value,
          page_size: userPageSize.value,
          q: userSearchQ.value.trim() || undefined,
        },
      }),
      http.get('/api/admin/sessions/online-users').catch(() => ({ data: { users: [] } }))
    ])
    
    const usersListRaw = usersRes.data.users || []
    const onlineUsers = onlineRes.data.users || []
    
    // 创建在线用户 ID 集合
    const onlineUserIds = new Set(onlineUsers.map(u => u.user_id))
    
    // 标记每个用户是否有会话
    usersList.value = usersListRaw.map(user => ({
      ...user,
      has_session: onlineUserIds.has(user.id)
    }))
    
    userTotal.value = usersRes.data.total ?? 0
    if (usersRes.data.pdf_max_pages_global != null && usersRes.data.pdf_max_pages_global !== '') {
      usersPdfGlobalCap.value = Math.max(1, Number(usersRes.data.pdf_max_pages_global))
    }
  } catch {
    usersList.value = []
    userTotal.value = 0
  } finally {
    usersLoading.value = false
  }
}

function openUserEdit(row) {
  // 禁止编辑其他管理员账号
  if (row.is_admin && row.username !== username.value) {
    ElMessage.warning('不能编辑其他管理员账号')
    return
  }
  
  userEditForm.id = row.id
  userEditForm.username = row.username
  userEditForm.email = row.email
  userEditForm.phone = row.phone || ''
  userEditForm.is_admin = !!row.is_admin
  userEditForm.is_active = !!row.is_active
  userEditForm.new_password = ''
  userEditForm.is_self = row.username === username.value
  userEditForm.is_target_other_admin = false // 已经在前面的检查中阻止了
  userEditForm.pdf_use_default = row.pdf_max_pages == null
  userEditForm.pdf_max_pages = row.pdf_max_pages != null ? row.pdf_max_pages : 80
  userEditForm.image_output_use_default = row.image_output_mode == null
  userEditForm.image_output_mode = row.image_output_mode || 'base64'
  userEditVisible.value = true
}

function resetUserEditForm() {
  userEditForm.new_password = ''
  userEditForm.pdf_max_pages = 80
  userEditForm.pdf_use_default = true
  userEditForm.image_output_mode = 'base64'
  userEditForm.image_output_use_default = true
}

async function submitUserEdit() {
  if (userEditForm.new_password && userEditForm.new_password.length < 8) {
    ElMessage.warning('新密码至少 8 位')
    return
  }
  userSaveLoading.value = true
  try {
    const body = {
      is_admin: userEditForm.is_admin,
      is_active: userEditForm.is_active,
      pdf_max_pages: userEditForm.pdf_use_default ? null : userEditForm.pdf_max_pages,
      image_output_mode: userEditForm.image_output_use_default ? null : userEditForm.image_output_mode,
    }
    if (userEditForm.new_password) body.new_password = userEditForm.new_password
    await http.patch(`/api/admin/users/${userEditForm.id}`, body)
    ElMessage.success('已保存')
    userEditVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message)
  } finally {
    userSaveLoading.value = false
  }
}

// ==================== 会话管理函数 ====================

/** 查看用户会话 */
async function viewUserSession(row) {
  sessionUserId.value = row.id
  sessionDialogVisible.value = true
  sessionLoading.value = true
  sessionData.has_session = false
  sessionData.session = null
  
  try {
    const { data } = await http.get(`/api/admin/users/${row.id}/session`)
    sessionData.has_session = data.has_session
    sessionData.session = data.session || null
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '获取会话信息失败')
    sessionData.has_session = false
  } finally {
    sessionLoading.value = false
  }
}

/** 确认踢出用户（从表格直接点击） */
async function kickUserConfirm(row) {
  try {
    await ElMessageBox.confirm(
      `确定要踢出用户「${row.username}」吗？\n\n该用户的 Token 将立即失效，需要重新登录。`,
      '踢出用户',
      { type: 'warning', confirmButtonText: '确定踢出', cancelButtonText: '取消' }
    )
    await doKickUser(row.id, row.username)
  } catch {
    // 用户取消
  }
}

/** 确认踢出用户（从会话对话框点击） */
async function confirmKickUser() {
  if (!sessionData.session) return
  
  try {
    await ElMessageBox.confirm(
      `确定要踢出用户「${sessionData.session.username}」吗？\n\n该用户的 Token 将立即失效，需要重新登录。`,
      '踢出用户',
      { type: 'warning', confirmButtonText: '确定踢出', cancelButtonText: '取消' }
    )
    await doKickUser(sessionUserId.value, sessionData.session.username)
    sessionDialogVisible.value = false
  } catch {
    // 用户取消
  }
}

/** 执行踢出操作 */
async function doKickUser(userId, username) {
  kickingUser.value = true
  try {
    const { data } = await http.post(`/api/admin/users/${userId}/kick`)
    ElMessage.success(data.message || `已踢出用户 ${username}`)
    // 刷新用户列表
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '踢出用户失败')
  } finally {
    kickingUser.value = false
  }
}

function openCreateUserDialog() {
  createUserVisible.value = true
}

function resetCreateUserForm() {
  createUserForm.username = ''
  createUserForm.email = ''
  createUserForm.password = ''
  createUserForm.confirmPassword = ''
  createUserForm.is_admin = false
  createUserForm.is_active = true
  createUserForm.pdf_max_pages = 80
  createUserForm.pdf_use_default = true
  createUserForm.image_output_mode = 'base64'
  createUserForm.image_output_use_default = true
  // 清除表单验证状态
  if (createUserFormRef.value) {
    createUserFormRef.value.clearValidate()
  }
}

async function submitCreateUser() {
  // 先触发表单验证
  if (!createUserFormRef.value) return
  
  try {
    await createUserFormRef.value.validate()
  } catch (err) {
    return // 验证失败，不继续执行
  }
  
  // 再次检查密码
  if (createUserForm.password !== createUserForm.confirmPassword) {
    ElMessage.error('两次输入密码不一致')
    return
  }
  
  createUserLoading.value = true
  try {
    const body = {
      username: createUserForm.username.trim(),
      email: createUserForm.email.trim().toLowerCase(),
      password: createUserForm.password,
      is_admin: createUserForm.is_admin,
      is_active: createUserForm.is_active,
      pdf_max_pages: createUserForm.pdf_use_default ? null : createUserForm.pdf_max_pages,
      image_output_mode: createUserForm.image_output_use_default ? null : createUserForm.image_output_mode,
    }
    
    const { data } = await http.post('/api/admin/users/create', body)
    ElMessage.success(data.message || '用户创建成功')
    createUserVisible.value = false
    await loadUsers()
  } catch (e) {
    const errorMsg = e.response?.data?.detail || e.message || '创建失败'
    ElMessage.error(errorMsg)
  } finally {
    createUserLoading.value = false
  }
}

async function batchUsersActive(isActive) {
  const rows = usersSelection.value
  if (!rows.length) return
  const verb = isActive ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${rows.length} 个账号批量${verb}吗？`,
      `批量${verb}`,
      { type: isActive ? 'info' : 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  usersBatchLoading.value = true
  try {
    const { data } = await http.post('/api/admin/users/batch', {
      user_ids: rows.map((r) => r.id),
      is_active: isActive,
    })
    const ok = (data.updated && data.updated.length) || 0
    const failed = data.failed || []
    if (failed.length) {
      const sample = failed
        .slice(0, 3)
        .map((f) => `#${f.id}: ${f.detail}`)
        .join('；')
      ElMessage.warning(
        `已${verb} ${ok} 个；${failed.length} 个未变更${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`
      )
    } else {
      ElMessage.success(`已${verb} ${ok} 个账号`)
    }
    usersSelection.value = []
    usersTableRef.value?.clearSelection?.()
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '批量操作失败')
  } finally {
    usersBatchLoading.value = false
  }
}

async function batchUsersAdmin(isAdminFlag) {
  const rows = usersSelection.value
  if (!rows.length) return
  const verb = isAdminFlag ? '设为管理员' : '取消管理员'
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${rows.length} 个账号批量${verb}吗？`,
      `批量${verb}`,
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  usersBatchLoading.value = true
  try {
    const { data } = await http.post('/api/admin/users/batch', {
      user_ids: rows.map((r) => r.id),
      is_admin: isAdminFlag,
    })
    const ok = (data.updated && data.updated.length) || 0
    const failed = data.failed || []
    if (failed.length) {
      const sample = failed
        .slice(0, 3)
        .map((f) => `#${f.id}: ${f.detail}`)
        .join('；')
      ElMessage.warning(
        `已${verb} ${ok} 个；${failed.length} 个未变更${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`
      )
    } else {
      ElMessage.success(`已${verb} ${ok} 个账号`)
    }
    usersSelection.value = []
    usersTableRef.value?.clearSelection?.()
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '批量操作失败')
  } finally {
    usersBatchLoading.value = false
  }
}

async function openBatchPdfDialog() {
  const rows = usersSelection.value
  if (!rows.length) return
  try {
    await ElMessageBox.confirm(
      `您即将批量设置「PDF 解析页数上限」，将作用于已勾选的 ${rows.length} 个用户（不含管理员）。请确认用户列表无误；误操作将影响用户解析配额。`,
      '操作警告',
      { type: 'warning', confirmButtonText: '已了解，继续', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  batchPdfUseDefault.value = true
  batchPdfPages.value = 80
  batchPdfDialogVisible.value = true
}

async function submitBatchPdf() {
  const rows = usersSelection.value
  if (!rows.length) return
  if (!batchPdfUseDefault.value && (!batchPdfPages.value || batchPdfPages.value < 1)) {
    ElMessage.warning('请填写有效的页数（≥1）或改为「与系统全局一致」')
    return
  }
  const desc = batchPdfUseDefault.value
    ? '与系统全局一致（清除个人上限）'
    : `个人上限 ${batchPdfPages.value} 页`
  try {
    await ElMessageBox.confirm(
      `确认为 ${rows.length} 个用户批量设置：${desc}？提交后立即生效。`,
      '确认提交',
      { type: 'warning', confirmButtonText: '确认设置', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  usersBatchLoading.value = true
  try {
    const { data } = await http.post('/api/admin/users/batch-pdf-pages', {
      user_ids: rows.map((r) => r.id),
      pdf_max_pages: batchPdfUseDefault.value ? null : batchPdfPages.value,
    })
    const ok = (data.updated && data.updated.length) || 0
    const failed = data.failed || []
    if (failed.length) {
      const sample = failed
        .slice(0, 3)
        .map((f) => `#${f.id}: ${f.detail}`)
        .join('；')
      ElMessage.warning(
        `已更新 ${ok} 个；${failed.length} 个未变更${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`
      )
    } else {
      ElMessage.success(`已更新 ${ok} 个用户的解析页数设置`)
    }
    batchPdfDialogVisible.value = false
    usersSelection.value = []
    usersTableRef.value?.clearSelection?.()
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '批量设置失败')
  } finally {
    usersBatchLoading.value = false
  }
}

async function batchUsersDelete() {
  const rows = usersSelection.value
  if (!rows.length) {
    ElMessage.warning('请先勾选要删除的用户')
    return
  }
  const list = rows.map((r) => r.username)
  const nameLine =
    list.length <= 12 ? list.join('、') : `${list.slice(0, 12).join('、')}…（共 ${rows.length} 人）`
  try {
    await ElMessageBox.confirm(
      `将永久删除以下用户账号，并删除其全部解析任务记录（数据库与关联数据），不可恢复。\n\n${nameLine}`,
      '确认删除用户',
      {
        type: 'error',
        confirmButtonText: '我确认删除',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true,
      }
    )
  } catch {
    return
  }
  usersBatchLoading.value = true
  try {
    const { data } = await http.post('/api/admin/users/batch-delete', {
      user_ids: rows.map((r) => r.id),
    })
    const ok = (data.deleted && data.deleted.length) || 0
    const failed = data.failed || []
    if (failed.length) {
      const sample = failed
        .slice(0, 3)
        .map((f) => `#${f.id}: ${f.detail}`)
        .join('；')
      ElMessage.warning(
        `已删除 ${ok} 个；${failed.length} 个未删除${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`
      )
    } else {
      ElMessage.success(`已删除 ${ok} 个用户`)
    }
    usersSelection.value = []
    usersTableRef.value?.clearSelection?.()
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '批量删除失败')
  } finally {
    usersBatchLoading.value = false
  }
}

async function loadCacheList() {
  cacheLoading.value = true
  cacheSelection.value = []
  try {
    const { data } = await http.get('/api/jobs', { params: { page: 1, page_size: 200 } })
    const jobs = data.jobs || []
    cacheRows.value = jobs.filter((j) => j.clearable)
  } catch {
    cacheRows.value = []
  } finally {
    cacheLoading.value = false
  }
}

async function clearCache() {
  const ids = cacheSelection.value.map((r) => r.job_id)
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(`确定删除选中 ${ids.length} 个任务的输出目录？此操作不可恢复。`, '确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    const { data } = await http.post('/api/jobs/clear-cache', { job_ids: ids })
    await loadCacheList()
    await loadRecords()
    ElMessage.success(`已清除 ${data.cleared?.length ?? 0} 个任务缓存`)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(String(e.response?.data?.detail || e.message || e))
  }
}

function waitForJobWs(jobId) {
  return new Promise((resolve, reject) => {
    if (ws) {
      try {
        ws.close()
      } catch {
        /* */
      }
    }
    currentJobId.value = jobId
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/ws/${jobId}`
    const sock = new WebSocket(url)
    ws = sock

    sock.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'progress') {
        progressPct.value = data.progress
        progressMsg.value = data.message || ''
      } else if (data.type === 'error') {
        parseErr.value = data.message
        currentJobId.value = null
        try {
          sock.close()
        } catch {
          /* */
        }
        reject(new Error(data.message || '解析失败'))
      } else if (data.type === 'completion') {
        progressPct.value = 100
        progressMsg.value = data.user_stopped ? '已停止，可下载当前已生成部分。' : '处理完成！'
        resultPartial.value = !!data.partial
        currentJobId.value = null
        try {
          sock.close()
        } catch {
          /* */
        }
        resolve(data)
      }
    }

    sock.onerror = () => {
      parseErr.value = 'WebSocket 连接失败'
      currentJobId.value = null
      reject(new Error('WebSocket 连接失败'))
    }
  })
}

async function startParse() {
  console.log('[调试] startParse 被调用')
  const queue = [...parseQueue.value]
  console.log('[调试] 队列长度:', queue.length)
  console.log('[调试] hasQueue:', hasQueue.value)
  console.log('[调试] parsing:', parsing.value)
  
  if (!queue.length) {
    console.warn('[调试] 队列为空，退出')
    return
  }
  
  batchAbort.value = false
  parseErr.value = ''
  parseBatchResults.value = []
  showResult.value = false
  resultPartial.value = false
  resultJobId.value = null
  parsing.value = true
  showProgress.value = true
  progressPct.value = 0
  const p = prompt.value.trim()
  const results = []
  const total = queue.length
  
  console.log('[调试] 开始处理', total, '个文件')

  for (let i = 0; i < queue.length; i++) {
    if (batchAbort.value) break
    parseErr.value = ''
    const item = queue[i]
    const name = item.file.name
    progressMsg.value =
      total > 1 ? `（${i + 1}/${total}）${name}：正在上传…` : '正在上传文件…'

    const fd = new FormData()
    fd.append('file', item.file)
    if (p) fd.append('prompt', p)
    if (/\.pdf$/i.test(name)) {
      fd.append('pdf_pages', String(effectivePdfPagesForItem(item)))
    }

    try {
      const { data } = await http.post('/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      progressPct.value = 0
      progressMsg.value = total > 1 ? `（${i + 1}/${total}）${name}：解析中…` : '正在解析文件…'
      await waitForJobWs(data.job_id)
      results.push({ ok: true, job_id: data.job_id, filename: name })
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || '失败'
      parseErr.value = msg
      results.push({ ok: false, filename: name, error: msg })
    }
  }

  parseBatchResults.value = results
  parsing.value = false
  showProgress.value = false
  currentJobId.value = null
  if (ws) {
    try {
      ws.close()
    } catch {
      /* */
    }
    ws = null
  }

  const anyOk = results.some((r) => r.ok)
  showResult.value = anyOk
  if (anyOk) {
    const lastOk = [...results].reverse().find((r) => r.ok)
    if (lastOk) resultJobId.value = lastOk.job_id
  }

  if (!batchAbort.value && results.length && results.every((r) => r.ok)) {
    parseQueue.value = []
    ElMessage.success(`已完成 ${results.length} 个文件的解析`)
  } else if (batchAbort.value) {
    ElMessage.info('已停止，后续文件未继续解析')
  } else if (results.some((r) => !r.ok)) {
    ElMessage.warning('部分文件未成功，请查看说明或生成记录')
  }
}

async function stopJob() {
  batchAbort.value = true
  if (!currentJobId.value) return
  try {
    await http.post(`/api/jobs/${encodeURIComponent(currentJobId.value)}/stop`)
    // 保持进度条显示，更新提示信息
    progressMsg.value = '正在停止…请稍候'
    // 不立即隐藏进度条，等待 WebSocket 返回 completion 消息
  } catch (e) {
    console.error('停止请求失败:', e)
    // 即使请求失败，也标记为停止
    progressMsg.value = '停止请求已发送'
  }
}
</script>

<style scoped>
.hidden-file {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

/* 文档解析：上传区上方的简要说明（与 platform.css 中 .lead / .supported-types 解耦，避免长段文字） */
.parse-page-intro {
  margin-bottom: 20px;
}
.parse-page-lead {
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.55;
  /* 移除 max-width 限制，让文字自然显示，只在窄屏时自动换行 */
}
.parse-formats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  margin-bottom: 10px;
}
.parse-formats-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  opacity: 0.9;
}
.parse-format-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.fmt-chip {
  display: inline-block;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  background: rgba(61, 214, 245, 0.08);
  border: 1px solid rgba(61, 214, 245, 0.22);
  border-radius: 999px;
  line-height: 1.2;
}
.fmt-chip-pdf {
  background: rgba(147, 112, 219, 0.1);
  border-color: rgba(147, 112, 219, 0.3);
}
.fmt-chip-cache-fail {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.35);
}
.parse-page-note {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
  /* 移除 max-width 限制，让文字自然显示 */
}
.parse-page-details {
  font-size: 13px;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0 14px;
  background: var(--bg-elevated);
}
.parse-page-details summary {
  cursor: pointer;
  padding: 11px 0;
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
  list-style: none;
  user-select: none;
}
.parse-page-details summary::-webkit-details-marker {
  display: none;
}
.parse-page-details summary::after {
  content: '▸';
  float: right;
  opacity: 0.45;
  font-size: 12px;
  transition: transform 0.2s ease;
}
.parse-page-details[open] summary::after {
  transform: rotate(90deg);
}
.parse-page-details-list {
  margin: 0 0 14px;
  padding-left: 1.15em;
  line-height: 1.65;
}
.parse-page-details-list li + li {
  margin-top: 6px;
}
.parse-page-details code {
  font-size: 12px;
  background: rgba(0, 0, 0, 0.28);
  padding: 2px 6px;
  border-radius: 4px;
}

.parse-prompt-field .parse-prompt-lead {
  margin: 0 0 10px;
  font-size: 13px;
  line-height: 1.55;
  /* 移除 max-width 限制，让文字自然显示 */
}
.parse-prompt-details {
  margin-top: 12px;
}
.parse-prompt-example-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 10px;
}
.parse-prompt-pick {
  flex-shrink: 0;
  appearance: none;
  border: 1px solid rgba(61, 214, 245, 0.35);
  background: rgba(61, 214, 245, 0.1);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  line-height: 1.3;
}
.parse-prompt-pick:hover {
  background: rgba(61, 214, 245, 0.18);
}

.records-actions-cell {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 4px 10px;
  text-align: right;
}
.records-actions-del,
.records-actions-del-hint {
  margin-left: 0 !important;
}

.workspace-layout {
  display: flex;
  min-height: 100vh;
  width: 100%;
  align-items: stretch;
}

.workspace-sider {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: rgba(10, 16, 30, 0.92);
  border-right: 1px solid var(--border);
  backdrop-filter: blur(10px);
}

.workspace-sider-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(2px);
}

.workspace-layout.is-mobile .workspace-sider {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 1001;
  width: min(280px, 86vw);
  height: 100vh;
  height: 100dvh;
  transform: translateX(-100%);
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: none;
}

.workspace-layout.is-mobile .workspace-sider.is-open {
  transform: translateX(0);
  box-shadow: 8px 0 28px rgba(0, 0, 0, 0.4);
}

.sider-brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 18px 16px;
  border-bottom: 1px solid var(--border);
}

.sider-brand .brand {
  font-size: 1.05rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sider-close-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
}

.sider-close-btn:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.1);
}

.sider-menu {
  flex: 1;
  border-right: none !important;
  padding: 8px 0 24px;
}

.sider-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin: 2px 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 菜单图标样式 */
.menu-icon {
  font-size: 18px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  flex-shrink: 0;
}

.workspace-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 15px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(10, 16, 30, 0.55);
  backdrop-filter: blur(8px);
  gap: 10px;
}

.workspace-layout.is-mobile .workspace-header {
  padding: 10px 12px;
}

.workspace-header-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.nav-toggle {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-left: -6px;
  padding: 0;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.nav-toggle:hover,
.nav-toggle:focus-visible {
  background: rgba(255, 255, 255, 0.07);
  outline: none;
}

.nav-toggle-bars {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 20px;
  height: 14px;
}

.nav-toggle-bars span {
  display: block;
  height: 2px;
  background: currentColor;
  border-radius: 1px;
  opacity: 0.92;
}

.workspace-header-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* 返回首页链接样式 */
.home-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  color: var(--text);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  cursor: pointer;
}

.home-link:hover {
  background: rgba(99, 102, 241, 0.15);
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.home-icon {
  font-size: 16px;
  line-height: 1;
}

.home-text {
  white-space: nowrap;
}

.workspace-layout.is-mobile .user-pill {
  font-size: 12px;
  max-width: 42vw;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-body {
  flex: 1;
  width: 100%;
  min-width: 0;
  padding: 16px 24px 40px;
  overflow: auto;
  box-sizing: border-box;
}

.workspace-layout.is-mobile .workspace-body {
  padding: 12px 12px 32px;
}

.workspace-layout.is-mobile .table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  width: 100%;
}

/* 生成记录表格响应式优化 */
.records-container .table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.records-container :deep(.el-table) {
  min-width: 900px; /* 确保表格有最小宽度，支持横向滚动 */
}

/* 缓存清除表格响应式优化 */
.cache-container .table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.cache-container :deep(.el-table) {
  min-width: 600px;
}

@media (max-width: 768px) {
  .records-container :deep(.el-table) {
    min-width: 800px;
  }
  
  .records-actions-cell {
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }
  
  .records-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .records-toolbar > * {
    width: 100%;
    max-width: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-layout.is-mobile .workspace-sider {
    transition: none;
  }
}

/* 覆盖 platform.css 中 .view-panel .container { max-width: 920px }，右侧主区占满可用宽度 */
.workspace-body .view-panel .container:not(.narrow-card) {
  max-width: none;
  width: 100%;
  margin-left: 0;
  margin-right: 0;
}

.workspace-body .view-panel .container.narrow-card {
  max-width: 440px;
  margin-left: auto;
  margin-right: auto;
}

.records-toolbar,
.users-pagination {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.records-toolbar:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

.records-pagination,
.users-pagination {
  margin-top: 20px;
  margin-bottom: 0;
  justify-content: flex-end;
  padding: 12px 0;
}

.btn-danger-outline {
  border: 1px solid rgba(245, 108, 108, 0.5);
  background: rgba(245, 108, 108, 0.08);
  color: var(--danger);
  transition: all 0.3s ease;
}

.btn-danger-outline:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.15);
  border-color: var(--danger);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
  transform: translateY(-2px);
}

:deep(.topbar .el-button.is-link) {
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 8px 16px;
  border-radius: 8px;
}

:deep(.topbar .el-button.is-link:hover) {
  color: var(--text);
}

.settings-h3 {
  margin: 0 0 16px;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-h3::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 20px;
  background: linear-gradient(180deg, var(--accent), var(--accent-dim));
  border-radius: 2px;
}

.settings-container {
  animation: fadeInUp 0.6s ease-out;
}

.settings-header {
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 2px solid rgba(99, 102, 241, 0.15);
}

.settings-header h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 12px;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}

.settings-icon {
  font-size: 2rem;
  animation: rotate 20s linear infinite;
  display: inline-block;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.settings-header .lead {
  margin: 0;
  font-size: 1rem;
  line-height: 1.6;
  color: var(--text-muted);
  max-width: 800px;
}

/* 通用页面头部样式 */
.page-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 2px solid rgba(99, 102, 241, 0.15);
  animation: fadeInUp 0.6s ease-out;
}

.page-header h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}

.page-icon {
  font-size: 2rem;
  display: inline-block;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

.page-header + .lead,
.page-header + p.lead {
  margin-top: 16px;
  font-size: 1rem;
  line-height: 1.6;
  color: var(--text-muted);
}

/* 缓存清除页面样式 */
.cache-container #cache-toolbar {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  transition: all 0.3s ease;
}

.cache-container #cache-toolbar:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

/* 密码修改页面样式 */
.password-container :deep(.el-input__wrapper) {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.password-container :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--accent) inset;
}

.password-container :deep(.el-alert) {
  border-radius: 8px;
  border-left: 4px solid;
}

/* 个人中心页面样式 */
.profile-container {
  max-width: 900px;
  margin: 0 auto;
}

.profile-section {
  margin-bottom: 32px;
  animation: fadeInUp 0.6s ease-out;
}

.profile-section:last-child {
  margin-bottom: 0;
}

.profile-section-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(99, 102, 241, 0.15);
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-info :deep(.el-descriptions__label),
.profile-quota :deep(.el-descriptions__label),
.profile-config :deep(.el-descriptions__label) {
  font-weight: 600;
  color: var(--text-muted);
  width: 140px;
}

.profile-info :deep(.el-descriptions__content),
.profile-quota :deep(.el-descriptions__content),
.profile-config :deep(.el-descriptions__content) {
  color: var(--text);
  font-weight: 500;
}

.quota-detail {
  margin-top: 8px;
  font-size: 0.9em;
  line-height: 1.6;
}

.profile-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.profile-actions .el-button {
  min-width: 120px;
  transition: all 0.3s ease;
}

.profile-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

/* 文档解析页面样式 */
.parse-container .upload-area {
  border: 2px dashed rgba(99, 102, 241, 0.3);
  border-radius: 12px;
  padding: 48px 32px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.03) 0%, rgba(168, 85, 247, 0.03) 100%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.parse-container .upload-area::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.1), transparent);
  transition: left 0.6s ease;
}

.parse-container .upload-area:hover::before {
  left: 100%;
}

.parse-container .upload-area:hover,
.parse-container .upload-area.dragover {
  border-color: var(--accent);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.15);
  transform: translateY(-2px);
}

/* 解析队列样式 */
.parse-queue {
  margin-top: 20px;
  border-radius: 12px;
  overflow: hidden;
  animation: slideIn 0.4s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.parse-queue-toolbar {
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
  border-bottom: 1px solid var(--border);
}

.parse-queue-title {
  font-weight: 700;
  color: var(--text);
  font-size: 1rem;
}

.parse-queue-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 300px;
  overflow-y: auto;
}

.parse-queue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  transition: all 0.2s ease;
}

.parse-queue-item:last-child {
  border-bottom: none;
}

.parse-queue-item:hover {
  background: rgba(99, 102, 241, 0.05);
}

.parse-queue-name {
  flex: 1;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.parse-queue-pdf-meta {
  font-size: 13px;
  color: var(--accent);
  font-weight: 600;
}

.parse-queue-pdf-meta.pdf-loading {
  color: #e6a23c;
  animation: pulse 1.5s ease-in-out infinite;
}

.parse-queue-pdf-meta.pdf-error {
  color: #f56c6c;
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.parse-queue-kb {
  font-size: 12px;
  color: var(--text-muted);
}

/* 按钮行样式 */
.btn-row-split {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
}

.btn-row-split .el-button {
  padding: 12px 24px;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-row-split .el-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
}

.btn-danger-outline {
  border: 1px solid rgba(245, 108, 108, 0.5);
  background: rgba(245, 108, 108, 0.08);
  color: var(--danger);
  transition: all 0.3s ease;
}

.btn-danger-outline:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.15);
  border-color: var(--danger);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
  transform: translateY(-2px);
}

/* 进度条样式 */
.progress-container {
  margin-top: 24px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  animation: fadeInUp 0.4s ease-out;
}

.progress-msg {
  margin-top: 12px;
  font-size: 14px;
  color: var(--text-muted);
  text-align: center;
}

.settings-summary {
  margin-bottom: 24px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
}

.settings-desc {
  margin-bottom: 0;
}

.settings-desc :deep(.el-descriptions__label) {
  font-weight: 600;
  color: var(--text);
  background: rgba(99, 102, 241, 0.05);
}

.settings-desc :deep(.el-descriptions__content) {
  color: var(--text-muted);
}

.settings-desc :deep(.el-descriptions__body) {
  background: transparent;
}

.settings-desc :deep(.el-tag) {
  padding: 4px 12px;
  border-radius: 6px;
  font-weight: 600;
}

.path-text {
  word-break: break-all;
  font-size: 13px;
  padding: 4px 8px;
  background: rgba(99, 102, 241, 0.05);
  border-radius: 4px;
  color: var(--accent);
  font-family: 'Courier New', monospace;
}

.form-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.6;
  padding-left: 12px;
  border-left: 2px solid var(--border);
}

.form-hint.muted {
  color: var(--text-muted);
  font-style: italic;
}

.admin-settings {
  margin-top: 32px;
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.settings-save-hint {
  margin-bottom: 20px;
  border-radius: 10px;
  border-left: 4px solid var(--accent);
}

.settings-save-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.settings-save-bar:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

.settings-save-bar--bottom {
  margin-top: 20px;
  margin-bottom: 0;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.settings-save-bar-tip {
  font-size: 13px;
}

.settings-save-bar .el-button {
  padding: 12px 24px;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.settings-save-bar .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
}

.admin-settings-form {
  margin-top: 0;
}

.admin-settings-tabs {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.admin-settings-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
  border-bottom: 2px solid rgba(99, 102, 241, 0.15);
}

.admin-settings-tabs :deep(.el-tabs__item) {
  font-weight: 600;
  color: var(--text-muted);
  transition: all 0.3s ease;
  padding: 16px 24px;
}

.admin-settings-tabs :deep(.el-tabs__item:hover) {
  color: var(--accent);
  background: rgba(99, 102, 241, 0.05);
}

.admin-settings-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent);
  font-weight: 700;
  background: transparent;
}

.admin-settings-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent-dim));
  border-radius: 3px 3px 0 0;
}

.admin-settings-tabs :deep(.el-tabs__content) {
  padding: 24px 20px 20px;
  background: rgba(255, 255, 255, 0.02);
}

.admin-settings-tabs :deep(.el-tab-pane) {
  max-width: 1200px; /* 增加宽度，从 900px 改为 1200px */
  animation: fadeIn 0.4s ease-out;
  overflow: visible !important; /* 确保 Tooltip 不被裁剪 */
}

/* 手风琴面板样式 - 按分组折叠 */
.settings-accordion {
  border: none;
  background: transparent;
}

.settings-accordion :deep(.el-collapse-item) {
  margin-bottom: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  overflow: visible; /* 允许 Tooltip 显示 */
  transition: all 0.3s ease;
}

.settings-accordion :deep(.el-collapse-item:hover) {
  border-color: var(--accent);
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
}

.settings-accordion :deep(.el-collapse-item__header) {
  height: auto;
  min-height: 56px;
  padding: 16px 18px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  background: transparent;
  border: none;
  line-height: 1.5;
  transition: all 0.3s ease;
}

.settings-accordion :deep(.el-collapse-item__header:hover) {
  color: var(--accent);
}

.settings-accordion :deep(.el-collapse-item__arrow) {
  color: var(--text-muted);
  font-size: 14px;
  margin-right: 8px;
}

.settings-accordion :deep(.el-collapse-item__wrap) {
  border: none;
  background: transparent;
  overflow: visible; /* 允许 Tooltip 显示 */
}

.settings-accordion :deep(.el-collapse-item__content) {
  padding: 0 18px 18px 18px;
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
  /* 移除 width/max-width 限制，让内容自然流动 */
}

/* 响应式优化 - 手风琴面板 */
@media (max-width: 768px) {
  .settings-accordion :deep(.el-collapse-item__header) {
    padding: 14px 16px;
    font-size: 14px;
  }
  
  .settings-accordion :deep(.el-collapse-item__content) {
    padding: 0 16px 16px 16px;
  }
  
  .accordion-panel-content :deep(.el-form-item__label) {
    font-size: 13px;
  }
  
  .accordion-panel-content :deep(.el-form-item__content) {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    margin-top: -8px;
    padding-left: 0;
  }
  
  .accordion-panel-content :deep(.el-input-number),
  .accordion-panel-content :deep(.el-select),
  .accordion-panel-content :deep(.el-switch) {
    width: 100% !important;
    max-width: 100% !important;
  }
}

/* 手风琴内部的内容区域 - 去掉配置项的圆角矩形 */
.accordion-panel-content {
  padding-top: 8px;
  /* 移除所有宽度限制，让内容自然显示 */
}

.accordion-panel-content :deep(.el-form-item) {
  margin-bottom: 16px;
  /* 移除边框、背景、圆角，只保留间距 */
  border: none;
  background: transparent;
  padding: 0;
  /* 移除 width: 100%，让 Element Plus 自己处理布局 */
}

.accordion-panel-content :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.accordion-panel-content :deep(.el-form-item__label) {
  display: inline-flex !important; /* 改回 inline-flex，让标签和提示图标在一行 */
  align-items: center;
  gap: 6px;
  padding: 0 0 10px !important;
  line-height: 1.5;
  font-weight: 600;
  color: var(--text);
  transition: color 0.3s ease;
  word-break: break-word; /* 长文本换行 */
}

.accordion-panel-content :deep(.el-form-item:hover .el-form-item__label) {
  color: var(--accent);
}

.accordion-panel-content :deep(.el-form-item__content) {
  display: flex;
  align-items: center; /* 垂直居中对齐 */
  min-height: 32px; /* 确保有足够高度 */
  margin-top: -12px; /* 向上移动更多，让开关与文本对齐 */
  padding-left: 16px; /* 左侧增加间距，与标签拉开距离 */
}

.accordion-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.settings-subsection-title {
  margin: 24px 0 14px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--accent);
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(99, 102, 241, 0.15);
}

.settings-subsection-title::before {
  content: '▸';
  font-size: 16px;
  color: var(--accent);
}

.settings-subsection-title:first-child {
  margin-top: 0;
}

.settings-label-with-tip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  line-height: 1.35;
}

.settings-label-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.settings-help-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  cursor: help;
  color: var(--text-muted);
  border: 1.5px solid var(--border);
  background: rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
  user-select: none;
  transition: all 0.3s ease;
}

.settings-help-trigger:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: rgba(99, 102, 241, 0.1);
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
}

.settings-help-trigger--title {
  margin-left: 2px;
}

.settings-tooltip-block {
  max-width: 320px;
  line-height: 1.6;
  font-size: 13px;
  padding: 4px 0;
}

.settings-tooltip-block div {
  margin: 4px 0;
}

.settings-tooltip-block strong {
  color: var(--accent);
  font-weight: 600;
}

.settings-tooltip-block code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #7dd3fc;
}

/* Element Plus Tooltip 自定义样式 - 匹配项目深色主题 */
/* 使用全局样式确保覆盖所有情况 */
:deep(.el-popper.is-dark),
:deep(.el-tooltip__popper.is-dark),
.el-popper.is-dark,
.el-tooltip__popper.is-dark {
  background: linear-gradient(135deg, #1a2540 0%, #141c2f 100%) !important;
  border: 1px solid rgba(99, 102, 241, 0.3) !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 
              0 0 0 1px rgba(99, 102, 241, 0.1),
              inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
  color: #e8eef8 !important;
  backdrop-filter: blur(8px);
  z-index: 9999 !important;
}

:deep(.el-popper.is-dark .el-popper__arrow)::before,
:deep(.el-tooltip__popper.is-dark .el-popper__arrow)::before,
.el-popper.is-dark .el-popper__arrow::before,
.el-tooltip__popper.is-dark .el-popper__arrow::before {
  background: linear-gradient(135deg, #1a2540 0%, #141c2f 100%) !important;
  border: 1px solid rgba(99, 102, 241, 0.3) !important;
}

:deep(.el-popper.is-dark .el-popper__content),
:deep(.el-tooltip__popper.is-dark .el-popper__content),
.el-popper.is-dark .el-popper__content,
.el-tooltip__popper.is-dark .el-popper__content {
  color: #e8eef8 !important;
  line-height: 1.6;
  padding: 2px 0;
}

/* Tooltip 内的链接和强调文本 */
:deep(.el-popper.is-dark a),
:deep(.el-tooltip__popper.is-dark a),
.el-popper.is-dark a,
.el-tooltip__popper.is-dark a {
  color: var(--accent) !important;
  text-decoration: none;
}

:deep(.el-popper.is-dark a:hover),
:deep(.el-tooltip__popper.is-dark a:hover),
.el-popper.is-dark a:hover,
.el-tooltip__popper.is-dark a:hover {
  text-decoration: underline;
}

/* Tooltip 内的代码块样式增强 */
:deep(.el-popper.is-dark code),
:deep(.el-tooltip__popper.is-dark code),
.el-popper.is-dark code,
.el-tooltip__popper.is-dark code,
.settings-tooltip-block code {
  background: rgba(0, 0, 0, 0.35) !important;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #7dd3fc !important;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  border: 1px solid rgba(125, 211, 252, 0.2);
}

/* 开关项：标签在上、控件在下，避免左右两列对齐造成的错行误点 */
.settings-panel-form--switch :deep(.el-form-item) {
  margin-bottom: 16px;
}

.settings-panel-form--switch :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.settings-panel-form--switch :deep(.el-form-item__label) {
  width: 100% !important;
  display: inline-flex !important;
  justify-content: flex-start;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 0 10px !important;
  line-height: 1.5;
  box-sizing: border-box;
  font-weight: 600;
  color: var(--text);
  transition: color 0.3s ease;
}

.settings-panel-form--switch .settings-form-item-switch:hover :deep(.el-form-item__label) {
  /* 移除标签悬停变色效果 */
  color: var(--text);
}

.settings-panel-form--switch :deep(.el-form-item__content) {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.settings-panel-form--switch .settings-form-item-switch {
  margin-bottom: 0;
  /* 移除圆角矩形卡片样式 */
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  transition: none;
  position: static;
}

.settings-panel-form--switch .settings-form-item-switch::before {
  /* 移除渐变背景伪元素 */
  display: none;
}

.settings-panel-form--switch .settings-form-item-switch:hover {
  /* 移除悬停效果 */
  border-color: transparent;
  background: transparent;
  box-shadow: none;
  transform: none;
}

.settings-panel-form--switch .settings-form-item-switch:hover::before {
  opacity: 0;
}

.settings-panel-form--switch .settings-form-item-switch+.settings-form-item-switch {
  margin-top: 12px;
}

.settings-panel-form--switch .settings-subsection-title+.settings-form-item-switch {
  margin-top: 0;
}

.settings-inline-hint {
  margin: 0 0 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(99, 102, 241, 0.05);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
}

.settings-dl-source {
  margin-bottom: 16px;
}

.settings-dl-source :deep(.el-radio-button__inner) {
  padding: 10px 20px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-weight: 600;
  color: var(--text);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  margin-left: 10px;
}

.settings-dl-source :deep(.el-radio-button__inner):hover {
  color: var(--accent);
  border-color: var(--accent);
  background: rgba(99, 102, 241, 0.1);
}

.settings-dl-source :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-color: #6366f1;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
  transform: translateY(-1px);
  font-weight: 700;
}

/* 下载状态信息样式 */
.download-status-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.status-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.status-label {
  color: #606266;
  font-weight: 500;
  min-width: 50px;
  flex-shrink: 0;
}

.status-value {
  color: #303133;
  word-break: break-all;
  flex: 1;
}

.status-path {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.03);
  padding: 2px 6px;
  border-radius: 4px;
}

.download-progress-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

/* 下载日志区域样式 */
.download-log-section {
  margin-top: 20px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(99, 102, 241, 0.08);
  border-bottom: 1px solid var(--border);
}

.log-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.log-content {
  max-height: 300px;
  overflow-y: auto;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
}

.log-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: #e0e0e0;
  font-family: 'Courier New', Consolas, monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-footer {
  padding: 12px 16px;
  background: rgba(99, 102, 241, 0.05);
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reload-error-text {
  font-size: 13px;
  color: #f56c6c;
  white-space: nowrap;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-5px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.settings-panel-form--paths :deep(.el-form-item__label) {
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--text);
}

.settings-panel-form--paths :deep(.el-input),
.settings-panel-form--paths :deep(.el-textarea) {
  transition: all 0.3s ease;
}

.settings-panel-form--paths :deep(.el-input:hover),
.settings-panel-form--paths :deep(.el-textarea:hover) {
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
}

.settings-panel-form--paths :deep(.el-input__wrapper),
.settings-panel-form--paths :deep(.el-textarea__inner) {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.settings-panel-form--paths :deep(.el-input__wrapper:hover),
.settings-panel-form--paths :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px var(--accent) inset;
}

.settings-panel-form--paths :deep(.el-input-number) {
  width: 100%;
}

.settings-panel-form--paths :deep(.el-select) {
  width: 100%;
}

.path-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.path-actions .el-button {
  transition: all 0.3s ease;
}

.path-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.path-btn-wrap {
  display: inline-block;
}

.path-picker-note {
  margin-top: 10px;
}

.mb-3 {
  margin-bottom: 12px;
}

.pdf-pages-label {
  display: block;
  margin-bottom: 10px;
}

.pdf-pages-slider-wrap {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.02);
}

.pdf-pages-slider-head {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
}

.pdf-pages-input-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.pdf-pages-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.pdf-pages-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.pdf-pages-help-icon {
  cursor: help;
  font-size: 16px;
  opacity: 0.6;
  transition: opacity 0.2s;
  user-select: none;
}

.pdf-pages-help-icon:hover {
  opacity: 1;
}

.pdf-pages-total-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 12px;
  white-space: nowrap;
}

.pdf-pages-loading-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 12px;
  white-space: nowrap;
}

.loading-dots::after {
  content: '...';
  animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
  0%, 20% { content: ''; }
  40% { content: '.'; }
  60% { content: '..'; }
  80%, 100% { content: '...'; }
}

.pdf-pages-input-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
}

.pdf-pages-input-num {
  width: 140px;
  max-width: 100%;
}

.pdf-pages-current {
  flex-shrink: 0;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  min-width: 88px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(61, 214, 245, 0.08);
  border: 1px solid rgba(61, 214, 245, 0.35);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.06) inset;
}

.pdf-pages-current-num {
  font-size: 1.35rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  color: var(--accent);
}

.pdf-pages-current-unit {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
}

.pdf-pages-slider-el {
  flex: 1;
  min-width: 0;
}

.pdf-pages-slider-el :deep(.el-slider__runway) {
  height: 8px;
  border-radius: 4px;
}

.pdf-pages-slider-el :deep(.el-slider__bar) {
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(61, 214, 245, 0.45), rgba(61, 214, 245, 0.95));
}

.pdf-pages-slider-el :deep(.el-slider__button) {
  width: 18px;
  height: 18px;
  border: 2px solid var(--accent);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.pdf-pages-slider-feet {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 12px;
}

.pdf-pages-range-min,
.pdf-pages-range-max {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  font-weight: 600;
  min-width: 2rem;
  text-align: center;
}

.pdf-pages-range-min {
  text-align: left;
}

.pdf-pages-range-max {
  text-align: right;
}

.pdf-pages-hint {
  font-size: 12px;
  line-height: 1.45;
  flex: 1;
  text-align: center;
}

.user-pdf-limit-row {
  margin-bottom: 8px;
}

.user-pdf-limit-note {
  margin: 8px 0 0;
  font-size: 12px;
}
.user-pdf-raw-hint {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.3;
}

.parse-queue {
  margin-top: 14px;
  padding: 12px 14px;
}
.parse-queue-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.parse-queue-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.parse-queue-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.parse-queue-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-top: 1px solid var(--border);
  font-size: 13px;
}
.parse-queue-item:first-of-type {
  border-top: none;
  padding-top: 0;
}
.parse-queue-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.parse-queue-pdf-meta {
  flex-shrink: 0;
  font-size: 12px;
  max-width: 12rem;
  white-space: nowrap;
}
.parse-queue-pdf-meta.pdf-loading {
  color: #e6a23c;
  font-weight: 500;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.parse-queue-kb {
  flex-shrink: 0;
  font-size: 12px;
}
.batch-result-block {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.batch-result-block:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.batch-result-title {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 14px;
}
.batch-result-err {
  color: var(--danger);
  font-size: 13px;
}
</style>
