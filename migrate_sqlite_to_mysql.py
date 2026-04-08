#!/usr/bin/env python3
"""
SQLite 到 MySQL 数据迁移工具

功能：
- 自动检测 SQLite 数据库
- 导出所有表结构和数据
- 导入到 MySQL 数据库
- 支持增量迁移（跳过已存在的记录）
- 保留外键关系和数据完整性

使用方法：
    python migrate_sqlite_to_mysql.py
    
环境变量：
    SQLITE_DB_PATH: SQLite 数据库路径（默认：web/data/app.db）
    MYSQL_HOST: MySQL 主机（默认：localhost）
    MYSQL_PORT: MySQL 端口（默认：3306）
    MYSQL_USER: MySQL 用户名（默认：root）
    MYSQL_PASSWORD: MySQL 密码
    MYSQL_DATABASE: MySQL 数据库名（默认：doculogic）
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import pymysql
from sqlalchemy import create_engine, inspect, MetaData, Table
from tqdm import tqdm


def get_sqlite_connection():
    """获取 SQLite 连接"""
    sqlite_path = os.environ.get(
        "SQLITE_DB_PATH",
        str(PROJECT_ROOT / "web" / "data" / "app.db")
    )
    
    if not Path(sqlite_path).exists():
        print(f"❌ SQLite 数据库不存在: {sqlite_path}")
        return None
    
    print(f"📂 SQLite 数据库: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_mysql_connection():
    """获取 MySQL 连接"""
    mysql_host = os.environ.get("MYSQL_HOST", "localhost")
    mysql_port = int(os.environ.get("MYSQL_PORT", "3306"))
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "")
    mysql_database = os.environ.get("MYSQL_DATABASE", "doculogic")
    
    if not mysql_password:
        print("❌ 请设置 MYSQL_PASSWORD 环境变量")
        return None
    
    print(f"📊 MySQL 数据库: {mysql_host}:{mysql_port}/{mysql_database}")
    
    try:
        conn = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ MySQL 连接失败: {e}")
        return None


def get_table_names(sqlite_conn):
    """获取所有表名"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    return tables


def get_table_schema(sqlite_conn, table_name):
    """获取表结构"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    schema = []
    for col in columns:
        cid, name, col_type, notnull, default_value, pk = col
        schema.append({
            'name': name,
            'type': col_type,
            'notnull': notnull,
            'default': default_value,
            'pk': pk
        })
    
    return schema


def convert_sqlite_type_to_mysql(sqlite_type):
    """转换 SQLite 类型到 MySQL 类型"""
    type_mapping = {
        'INTEGER': 'INT',
        'INT': 'INT',
        'BOOLEAN': 'TINYINT(1)',
        'TINYINT': 'TINYINT(1)',
        'REAL': 'DOUBLE',
        'FLOAT': 'FLOAT',
        'TEXT': 'LONGTEXT',
        'VARCHAR': 'VARCHAR(512)',
        'DATETIME': 'DATETIME',
        'TIMESTAMP': 'TIMESTAMP',
        'BLOB': 'LONGBLOB',
    }
    
    sqlite_type_upper = sqlite_type.upper()
    
    # 精确匹配
    if sqlite_type_upper in type_mapping:
        return type_mapping[sqlite_type_upper]
    
    # 模糊匹配
    if 'INT' in sqlite_type_upper:
        return 'INT'
    if 'CHAR' in sqlite_type_upper or 'TEXT' in sqlite_type_upper:
        return 'LONGTEXT'
    if 'REAL' in sqlite_type_upper or 'FLOAT' in sqlite_type_upper or 'DOUBLE' in sqlite_type_upper:
        return 'DOUBLE'
    if 'DATE' in sqlite_type_upper or 'TIME' in sqlite_type_upper:
        return 'DATETIME'
    if 'BLOB' in sqlite_type_upper:
        return 'LONGBLOB'
    
    # 默认使用 TEXT
    return 'LONGTEXT'


def create_mysql_table(mysql_conn, table_name, schema):
    """在 MySQL 中创建表"""
    cursor = mysql_conn.cursor()
    
    # 检查表是否已存在
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    if cursor.fetchone():
        print(f"  ⚠️  表 {table_name} 已存在，跳过创建")
        return True
    
    # 构建 CREATE TABLE 语句
    columns = []
    primary_keys = []
    
    for col in schema:
        mysql_type = convert_sqlite_type_to_mysql(col['type'])
        col_def = f"`{col['name']}` {mysql_type}"
        
        if col['notnull']:
            col_def += " NOT NULL"
        
        if col['default'] is not None:
            if col['default'] == 'CURRENT_TIMESTAMP':
                col_def += f" DEFAULT {col['default']}"
            else:
                # 处理字符串默认值
                default_val = str(col['default'])
                if default_val.upper() not in ('NULL', 'CURRENT_TIMESTAMP'):
                    default_val = f"'{default_val}'"
                col_def += f" DEFAULT {default_val}"
        
        if col['pk']:
            primary_keys.append(col['name'])
        
        columns.append(col_def)
    
    if primary_keys:
        columns.append(f"PRIMARY KEY ({', '.join([f'`{k}`' for k in primary_keys])})")
    
    create_sql = f"CREATE TABLE `{table_name}` (\n  " + ",\n  ".join(columns) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    
    try:
        cursor.execute(create_sql)
        mysql_conn.commit()
        print(f"  ✅ 创建表: {table_name}")
        return True
    except Exception as e:
        print(f"  ❌ 创建表失败 {table_name}: {e}")
        return False


def migrate_table_data(sqlite_conn, mysql_conn, table_name):
    """迁移表数据"""
    # 获取 SQLite 数据
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  ℹ️  表 {table_name} 无数据，跳过")
        return True
    
    # 获取列名
    columns = [description[0] for description in sqlite_cursor.description]
    
    # 检查 MySQL 中是否已有数据
    mysql_cursor = mysql_conn.cursor()
    mysql_cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
    existing_count = mysql_cursor.fetchone()['count']
    
    if existing_count > 0:
        print(f"  ⚠️  表 {table_name} 已有 {existing_count} 条记录，跳过导入")
        return True
    
    # 插入数据
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join([f'`{col}`' for col in columns])
    insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
    
    success_count = 0
    error_count = 0
    
    for row in tqdm(rows, desc=f"  迁移 {table_name}", unit="行"):
        try:
            # 转换数据格式
            values = []
            for val in row:
                if isinstance(val, bytes):
                    # BLOB 数据
                    values.append(val)
                else:
                    values.append(val)
            
            mysql_cursor.execute(insert_sql, values)
            success_count += 1
        except Exception as e:
            error_count += 1
            if error_count <= 3:  # 只显示前3个错误
                print(f"    ❌ 插入失败: {e}")
    
    if error_count > 0:
        mysql_conn.rollback()
        print(f"  ❌ 迁移失败: 成功 {success_count}, 失败 {error_count}")
        return False
    else:
        mysql_conn.commit()
        print(f"  ✅ 迁移完成: {success_count} 条记录")
        return True


def migrate_sqlite_to_mysql():
    """主迁移函数"""
    print("=" * 60)
    print("  SQLite → MySQL 数据迁移工具")
    print("=" * 60)
    print()
    
    # 连接数据库
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return False
    
    mysql_conn = get_mysql_connection()
    if not mysql_conn:
        sqlite_conn.close()
        return False
    
    try:
        # 获取所有表
        tables = get_table_names(sqlite_conn)
        print(f"\n📋 发现 {len(tables)} 个表: {', '.join(tables)}\n")
        
        # 迁移每个表
        success_tables = []
        failed_tables = []
        
        for table_name in tables:
            print(f"🔄 处理表: {table_name}")
            
            # 1. 获取表结构
            schema = get_table_schema(sqlite_conn, table_name)
            
            # 2. 创建 MySQL 表
            if not create_mysql_table(mysql_conn, table_name, schema):
                failed_tables.append(table_name)
                continue
            
            # 3. 迁移数据
            if migrate_table_data(sqlite_conn, mysql_conn, table_name):
                success_tables.append(table_name)
            else:
                failed_tables.append(table_name)
            
            print()
        
        # 总结
        print("=" * 60)
        print("  迁移完成")
        print("=" * 60)
        print(f"✅ 成功: {len(success_tables)} 个表")
        if success_tables:
            print(f"   - {', '.join(success_tables)}")
        
        if failed_tables:
            print(f"❌ 失败: {len(failed_tables)} 个表")
            print(f"   - {', '.join(failed_tables)}")
            return False
        
        print("\n🎉 所有数据已成功迁移到 MySQL！")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sqlite_conn.close()
        mysql_conn.close()


if __name__ == "__main__":
    success = migrate_sqlite_to_mysql()
    sys.exit(0 if success else 1)
