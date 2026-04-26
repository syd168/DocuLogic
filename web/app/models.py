"""
数据库模型定义

本模块定义了应用的所有数据库表结构，包括：
- User: 用户表，存储用户信息和权限
- VerificationCode: 验证码表，用于注册和找回密码
- ParseJob: 解析任务表，跟踪文档解析进度
- AppSettings: 系统配置表，存储全局设置
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """
    用户表
    
    存储系统用户的基本信息、认证凭据和权限配置。
    支持邮箱和手机号两种登录方式。
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # 邮箱地址（唯一）
    phone: Mapped[Optional[str]] = mapped_column(String(16), unique=True, nullable=True, index=True)  # 手机号（可选，唯一）
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 用户名（唯一）
    hashed_password: Mapped[str] = mapped_column(String(255))  # bcrypt 哈希后的密码
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否为管理员
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 账号是否激活
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)  # 连续失败登录次数
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 账号锁定截止时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 注册时间
    # 单用户 PDF 解析页数上限；None 表示与系统全局 pdf_max_pages 一致（随系统配置变化）
    pdf_max_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 是否允许下载图片资源（仅当输出模式为 separate 时生效）
    can_download_images: Mapped[bool] = mapped_column(Boolean, default=True)
    # 用户个人图片输出模式；None 表示跟随系统设置
    image_output_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    jobs: Mapped[list["ParseJob"]] = relationship("ParseJob", back_populates="user")  # 关联的解析任务


class VerificationCode(Base):
    """
    验证码表
    
    存储邮箱或手机验证码，用于用户注册和找回密码流程。
    验证码经过哈希处理，不直接存储明文。
    """
    __tablename__ = "verification_codes"
    __table_args__ = (
        UniqueConstraint('email', 'purpose', name='uq_email_purpose'),  # 防止重复验证码
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)  # 邮箱或手机号（合成键）
    code_hash: Mapped[str] = mapped_column(String(128))  # 验证码的哈希值
    expires_at: Mapped[datetime] = mapped_column(DateTime)  # 过期时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 创建时间
    purpose: Mapped[str] = mapped_column(String(16), default="register")  # 用途：register / forgot


class ParseJob(Base):
    """
    解析任务表
    
    跟踪文档解析任务的完整生命周期，包括状态、进度和结果。
    用于实现任务队列、WebSocket 实时推送和下载鉴权。
    """
    __tablename__ = "parse_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID 格式的任务 ID
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)  # 所属用户 ID
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 任务创建时间
    # processing | completed | stopped | failed
    status: Mapped[str] = mapped_column(String(32), default="processing")  # 任务状态
    original_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # 原始文件名
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 完成时间
    cache_cleared_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 缓存清除时间
    # 本次任务实际解析页数：单图 1；PDF 为已生成页数；失败或未落库为 NULL
    pages_parsed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="jobs")  # 关联的用户


class AppSettings(Base):
    """
    系统配置表（单例，id=1）
    
    存储全局系统配置，包括：
    - 用户注册和认证设置
    - PDF 解析限制
    - 邮件和短信服务配置
    - 输出格式和路径配置
    - 密码规则配置
    """
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 固定为 1（单例）
    registration_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许用户注册
    captcha_login_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # 登录时是否启用验证码
    captcha_register_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # 注册时是否启用验证码
    captcha_forgot_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # 找回密码时是否启用验证码
    pdf_max_pages: Mapped[int] = mapped_column(Integer, default=80)  # PDF 最大解析页数（全局默认）
    output_dir: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)  # 解析输出目录路径
    default_converter_id: Mapped[str] = mapped_column(String(64), default="logics-parsing-v2")  # 默认转换器 ID
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 最后更新时间
    # 邮件（SMTP）；密码仅存库内，接口不回显
    email_mock: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否使用模拟邮件（打印到日志）
    smtp_host: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # SMTP 服务器地址
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)  # SMTP 端口
    smtp_user: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # SMTP 用户名
    smtp_password: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # SMTP 密码（加密存储）
    smtp_from: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # 发件人地址
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否使用 TLS 加密

    # 注册 / 登录 / 找回：是否允许邮箱或手机号路径（关闭后对应前端入口隐藏）
    register_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许邮箱注册
    register_phone_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许手机注册
    login_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许邮箱登录
    login_phone_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许手机登录
    forgot_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许邮箱找回密码
    forgot_phone_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许手机找回密码

    # 短信：mock 时仅打印；否则向 sms_http_url POST JSON（见 sms_svc）
    sms_mock: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否使用模拟短信（打印到日志）
    sms_http_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)  # 短信 HTTP 接口 URL
    sms_http_secret: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # 短信接口密钥
    sms_http_headers_json: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)  # 自定义 HTTP 头（JSON 格式）
    sms_http_body_template: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)  # 请求体模板

    # 解析输出：是否在结果中显示页码标记（如 <!-- 第 X 页 --> 和 ## 第 X 页）
    show_page_numbers: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否在 Markdown 中显示页码

    # 图片输出模式：base64（嵌入 Markdown）/ separate（独立文件）/ none（不输出）
    image_output_mode: Mapped[str] = mapped_column(String(16), default="base64")  # 图片输出模式

    # 僵尸任务超时时长（分钟）：超过此时长且仍为 processing 状态的任务视为僵尸任务
    stale_job_timeout_minutes: Mapped[int] = mapped_column(Integer, default=10)

    # 登录超时时长（分钟）：用户无操作超过此时长后自动退出登录
    login_timeout_minutes: Mapped[int] = mapped_column(Integer, default=10)

    # 密码规则配置
    password_min_length: Mapped[int] = mapped_column(Integer, default=8)  # 密码最小长度
    password_require_uppercase: Mapped[bool] = mapped_column(Boolean, default=True)  # 要求大写字母
    password_require_lowercase: Mapped[bool] = mapped_column(Boolean, default=True)  # 要求小写字母
    password_require_digit: Mapped[bool] = mapped_column(Boolean, default=True)  # 要求数字
    password_require_special: Mapped[bool] = mapped_column(Boolean, default=False)  # 要求特殊字符
    
    # 文件上传限制（MB）
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, default=50)  # 最大上传文件大小（MB）
    
    # 是否允许多文件上传（一次可选择多个文件）
    allow_multi_file_upload: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否允许一次选择多个文件上传
