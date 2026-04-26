<template>
  <!-- 系统设置 -->
  <div class="view-panel">
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
          <el-descriptions-item label="单个文件最大解析页数">
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

        <div class="settings-save-bar settings-save-bar--top" style="margin-bottom: 10px;">
          <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
        </div>

        <div class="admin-settings-form">
          <el-tabs :model-value="adminSettingsTab" @update:model-value="$emit('update:admin-settings-tab', $event)"
            type="border-card" class="admin-settings-tabs">
            <el-tab-pane label="注册与安全" name="security">
              <el-collapse :model-value="activeSecurityPanels?.[0] || ''" accordion
                class="settings-accordion settings-accordion--security"
                @update:model-value="$emit('update:active-security-panels', $event ? [$event] : [])">

                <!-- 基础 -->
                <el-collapse-item class="settings-section-card" name="basic">
                  <template #title>
                    <div class="settings-accordion-title">
                      <span class="settings-accordion-title__icon">🔐</span>
                      <span class="settings-accordion-title__text">
                        <span class="settings-accordion-title__sub">注册设置</span>
                      </span>
                    </div>
                  </template>
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

                <!-- 图形验证码 -->
                <el-collapse-item class="settings-section-card" name="captcha">
                  <template #title>
                    <div class="settings-accordion-title">
                      <span class="settings-accordion-title__icon">🛡️</span>
                      <span class="settings-accordion-title__text">
                        <span class="settings-accordion-title__main">验证码设置</span>
                      </span>
                    </div>
                  </template>
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

                <!-- 解析限制 -->
                <el-collapse-item class="settings-section-card" name="parse_limits">
                  <template #title>
                    <div class="settings-accordion-title">
                      <span class="settings-accordion-title__icon">⚙️</span>
                      <span class="settings-accordion-title__text">
                        <span class="settings-accordion-title__main">解析设置</span>
                      </span>
                    </div>
                  </template>
                  <div class="accordion-panel-content">
                    <el-form-item>
                      <template #label>
                        <span class="settings-label-with-tip">单文件最大页数</span>
                        <el-tooltip placement="top" :show-after="300" effect="dark">
                          <template #content>
                            <div class="settings-tooltip-block">单个PDF文件允许最大页数上限。每个文件单独计算。</div>
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
                              开启后，解析结果是否包含页码标记（如 &lt;!-- 第 X 页 --&gt; 和 ## 第 X 页）。
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
                <el-collapse-item class="settings-section-card" name="task_management">
                  <template #title>
                    <div class="settings-accordion-title">
                      <span class="settings-accordion-title__icon">⏱️</span>
                      <span class="settings-accordion-title__text">
                        <span class="settings-accordion-title__main">任务管理</span>

                      </span>
                    </div>
                  </template>
                  <div class="accordion-panel-content">
                    <el-form-item>
                      <template #label>
                        <span class="settings-label-with-tip">僵尸任务超时（分钟）</span>
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
                        <span class="settings-label-with-tip">登录超时（分钟）</span>
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
                <el-collapse-item class="settings-section-card" name="password_rules">
                  <template #title>
                    <div class="settings-accordion-title">
                      <span class="settings-accordion-title__icon">🔑</span>
                      <span class="settings-accordion-title__text">
                        <span class="settings-accordion-title__main">密码规则</span>

                      </span>
                    </div>
                  </template>
                  <div class="accordion-panel-content">

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

                <!-- 文件上传限制 -->
                <el-collapse-item class="settings-section-card" name="upload">
                  <template #title>
                    <div class="settings-accordion-title">
                      <span class="settings-accordion-title__icon">📤</span>
                      <span class="settings-accordion-title__text">
                        <span class="settings-accordion-title__main">上传限制</span>

                      </span>
                    </div>
                  </template>
                  <div style="padding: 8px 0;">
                    <el-form-item>
                      <template #label>
                        <span class="settings-label-with-tip">上传文件大小</span>
                        <el-tooltip placement="top" :show-after="300" effect="dark">
                          <template #content>
                            <div class="settings-tooltip-block">
                              用户上传文件的最大允许大小（单位：MB）。<br><br>
                              <strong>注意：</strong>此配置仅控制后端校验，如需完整生效，还需同步修改 Nginx 的 <code>client_max_body_size</code>
                              配置。<br><br>
                              建议：Nginx 限制略大于此值（如后端 50MB，Nginx 设 55MB）
                            </div>
                          </template>
                          <span class="settings-help-trigger" aria-label="说明">?</span>
                        </el-tooltip>
                      </template>
                      <el-input-number v-model="adminForm.max_upload_size_mb" :min="1" :max="500" :step="10"
                        style="width: 200px" />
                      <span style="margin-left: 10px; color: var(--text-muted);">MB（范围：1-500）</span>
                    </el-form-item>

                    <el-form-item class="settings-form-item-switch">
                      <template #label>
                        <span class="settings-label-with-tip">多文件上传</span>
                        <el-tooltip placement="top" :show-after="300" effect="dark">
                          <template #content>
                            <div class="settings-tooltip-block">
                              开启后，用户可一次选择多个文件上传；关闭后，每次只能选择一个文件。
                            </div>
                          </template>
                          <span class="settings-help-trigger" aria-label="说明">?</span>
                        </el-tooltip>
                      </template>
                      <el-switch v-model="adminForm.allow_multi_file_upload" />
                    </el-form-item>

                    <!-- 实时验证提示 -->
                    <el-alert :title="'配置验证'" :type="uploadSizeValidation.type" :closable="false"
                      style="margin-top: 12px;">
                      <template #default>
                        <div v-html="uploadSizeValidation.message"></div>
                        <div v-if="!uploadSizeValidation.valid"
                          style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2);">
                          <strong>当前 Nginx 配置：</strong>{{ nginxConfig.max_body_size_mb }} MB<br>
                          <strong>推荐设置：</strong>
                          <code
                            style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px;">NGINX_MAX_BODY_SIZE={{ Math.ceil(adminForm.max_upload_size_mb * 1.1) }}m</code>
                        </div>
                      </template>
                    </el-alert>

                    <el-alert title="如何修改 Nginx 配置" type="info" :closable="false" style="margin-top: 12px;">
                      <template #default>
                        <p style="margin: 4px 0;"><strong>Docker 环境：</strong></p>
                        <ol style="margin: 8px 0; padding-left: 20px; line-height: 1.8;">
                          <li>编辑 <code>.env</code> 文件，设置 <code>NGINX_MAX_BODY_SIZE=XXm</code></li>
                          <li>执行 <code>cd docker && docker compose restart</code></li>
                        </ol>
                        <p style="margin: 8px 0 4px 0;"><strong>手动部署：</strong></p>
                        <ol style="margin: 8px 0; padding-left: 20px; line-height: 1.8;">
                          <li>编辑 Nginx 配置文件（通常在 <code>/etc/nginx/nginx.conf</code>）</li>
                          <li>在 <code>server</code> 块中添加：<code>client_max_body_size XXm;</code></li>
                          <li>执行 <code>nginx -s reload</code> 重载配置</li>
                        </ol>
                      </template>
                    </el-alert>
                  </div>
                </el-collapse-item>

              </el-collapse>
            </el-tab-pane>

            <el-tab-pane label="邮件 SMTP" name="email">
              <el-form label-position="top" class="settings-panel-form settings-panel-form--switch" @submit.prevent>
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
                  <el-input v-model="adminForm.smtp_password" type="password" show-password autocomplete="new-password"
                    placeholder="留空不修改已保存" />
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
              <el-form label-position="top" class="settings-panel-form settings-panel-form--switch" @submit.prevent>
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

          <div class="settings-save-bar settings-save-bar--bottom" style="margin-top: 10px;">
            <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isAdmin: { type: Boolean, required: true },
  settingsLoadError: { type: String, default: '' },
  settingsSummary: { type: Object, required: true },
  adminSaveLoading: { type: Boolean, required: true },
  saveAdminSettings: { type: Function, required: true },
  adminSettingsTab: { type: String, required: true },
  activeSecurityPanels: { type: Array, required: true },
  adminForm: { type: Object, required: true },
  uploadSizeValidation: { type: Object, required: true },
  nginxConfig: { type: Object, required: true },
})

defineEmits(['update:admin-settings-tab', 'update:active-security-panels'])
</script>
