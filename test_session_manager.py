#!/usr/bin/env python3
"""
测试 Token 黑名单和会话管理功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web'))

from app.session_manager import (
    revoke_token,
    is_token_blacklisted,
    create_user_session,
    get_user_session,
    destroy_user_session,
    kick_user,
    check_single_login,
    validate_token_with_session,
)
from app.auth_security import create_access_token


def test_token_blacklist():
    """测试 Token 黑名单功能"""
    print("\n=== 测试 Token 黑名单 ===")
    
    # 创建测试 token
    token = create_access_token({"sub": "1", "username": "test_user"})
    print(f"✅ 创建测试 Token: {token[:50]}...")
    
    # 检查是否在黑名单中（应该不在）
    result = is_token_blacklisted(token)
    print(f"📋 Token 在黑名单中？ {result} (预期: False)")
    assert not result, "新 token 不应该在黑名单中"
    
    # 将 token 加入黑名单
    success = revoke_token(token, reason="test")
    print(f"🚫 将 Token 加入黑名单: {success}")
    assert success, "应该成功加入黑名单"
    
    # 再次检查（应该在黑名单中）
    result = is_token_blacklisted(token)
    print(f"📋 Token 在黑名单中？ {result} (预期: True)")
    assert result, "token 应该在黑名单中"
    
    print("✅ Token 黑名单测试通过！\n")


def test_session_management():
    """测试会话管理功能"""
    print("\n=== 测试会话管理 ===")
    
    user_id = 2
    username = "session_test_user"
    token = create_access_token({"sub": str(user_id), "username": username})
    
    # 创建会话
    success = create_user_session(
        user_id=user_id,
        username=username,
        token=token,
        ip_address="192.168.1.100",
        user_agent="Test Browser",
        ttl_seconds=3600
    )
    print(f"✅ 创建用户会话: {success}")
    assert success, "应该成功创建会话"
    
    # 获取会话
    session = get_user_session(user_id)
    print(f"📋 获取会话: {session is not None}")
    assert session is not None, "应该能获取到会话"
    assert session["username"] == username, "用户名应该匹配"
    print(f"   - 用户名: {session['username']}")
    print(f"   - IP: {session['ip_address']}")
    print(f"   - User-Agent: {session['user_agent']}")
    
    # 销毁会话
    success = destroy_user_session(user_id, reason="test_logout")
    print(f"🗑️  销毁会话: {success}")
    assert success, "应该成功销毁会话"
    
    # 再次获取（应该不存在）
    session = get_user_session(user_id)
    print(f"📋 会话已销毁: {session is None}")
    assert session is None, "会话应该已被销毁"
    
    print("✅ 会话管理测试通过！\n")


def test_single_login():
    """测试单点登录功能"""
    print("\n=== 测试单点登录 ===")
    
    user_id = 3
    username = "single_login_user"
    
    # 第一次登录
    token1 = create_access_token({"sub": str(user_id), "username": username})
    create_user_session(user_id, username, token1, "192.168.1.1", "Browser 1")
    print(f"✅ 第一次登录: token1 = {token1[:30]}...")
    
    # 等待1秒，确保token不同
    import time
    time.sleep(1.1)
    
    # 第二次登录（应该替换第一次的会话）
    token2 = create_access_token({"sub": str(user_id), "username": username})
    print(f"🔄 准备第二次登录...")
    print(f"   - 检查用户 {user_id} 是否有旧会话")
    old_session = check_single_login(user_id, token2)  # 这会拉黑 token1
    print(f"🔄 第二次登录: token2 = {token2[:30]}...")
    if old_session:
        print(f"   - 检测到旧会话，将被替换")
        print(f"   - 旧 token: {old_session.get('token', '')[:30]}...")
    else:
        print(f"   - ⚠️ 没有检测到旧会话！")
    
    create_user_session(user_id, username, token2, "192.168.1.2", "Browser 2")
    
    # 验证 token1 是否被拉黑
    print(f"🔍 调试信息：")
    print(f"   - token1: {token1[:50]}...")
    from app.session_manager import cache
    blacklist_key = f"token_blacklist:{token1}"
    exists_in_redis = cache.exists(blacklist_key)
    print(f"   - Redis key '{blacklist_key}' 存在? {exists_in_redis}")
    
    token1_blacklisted = is_token_blacklisted(token1)
    print(f"📋 token1 已被拉黑: {token1_blacklisted} (预期: True)")
    assert token1_blacklisted, "旧 token 应该被拉黑"
    
    # 验证 token2 是否有效
    token2_valid = validate_token_with_session(token2, user_id)
    print(f"📋 token2 仍然有效: {token2_valid} (预期: True)")
    assert token2_valid, "新 token 应该有效"
    
    # 验证 token1 是否无效
    token1_valid = validate_token_with_session(token1, user_id)
    print(f"📋 token1 已失效: {not token1_valid} (预期: True)")
    assert not token1_valid, "旧 token 应该失效"
    
    print("✅ 单点登录测试通过！\n")


def test_kick_user():
    """测试踢出用户功能"""
    print("\n=== 测试踢出用户 ===")
    
    user_id = 4
    username = "kick_test_user"
    token = create_access_token({"sub": str(user_id), "username": username})
    
    # 创建会话
    create_user_session(user_id, username, token, "192.168.1.50", "Test Browser")
    print(f"✅ 用户 {username} 已登录")
    
    # 验证会话存在
    session = get_user_session(user_id)
    assert session is not None, "会话应该存在"
    print(f"📋 会话存在: {session['username']}")
    
    # 踢出用户
    success = kick_user(user_id, admin_username="admin")
    print(f"🚫 管理员踢出用户: {success}")
    assert success, "应该成功踢出用户"
    
    # 验证会话已销毁
    session = get_user_session(user_id)
    print(f"📋 会话已销毁: {session is None} (预期: True)")
    assert session is None, "会话应该已被销毁"
    
    # 验证 token 已被拉黑
    token_blacklisted = is_token_blacklisted(token)
    print(f"📋 Token 已被拉黑: {token_blacklisted} (预期: True)")
    assert token_blacklisted, "token 应该被拉黑"
    
    print("✅ 踢出用户测试通过！\n")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试 Token 黑名单和会话管理功能")
    print("=" * 60)
    
    try:
        test_token_blacklist()
        test_session_management()
        test_single_login()
        test_kick_user()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
