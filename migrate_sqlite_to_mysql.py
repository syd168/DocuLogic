#!/usr/bin/env python3
"""
SQLite 到 MySQL 数据迁移工具

功能：
- 从 SQLite 数据库导出数据
- 生成兼容 MySQL 的 SQL 文件
- 支持在本地或 Docker 环境中导入

使用方法：
    # 1. 导出 SQLite 数据为 SQL 文件
    python migrate_sqlite_to_mysql.py export
    
    # 2. 导入到 MySQL（需要设置环境变量）
    export MYSQL_PASSWORD=your_password
    python migrate_sqlite_to_mysql.py import

环境变量（仅导入时需要）：
    MYSQL_HOST: MySQL 主机（默认：localhost）
    MYSQL_PORT: MySQL 端口（默认：3306）
    MYSQL_USER: MySQL 用户名（默认：root）
    MYSQL_PASSWORD: MySQL 密码（必需）
    MYSQL_DATABASE: MySQL 数据库名（默认：doculogic）
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3


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
    
    if sqlite_type_upper in type_mapping:
        return type_mapping[sqlite_type_upper]
    
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
    
    return 'LONGTEXT'


def escape_mysql_value(value):
    """转义 MySQL 值"""
    if value is None:
        return 'NULL'
    elif isinstance(value, bytes):
        # BLOB 数据转换为十六进制
        return f"X'{value.hex()}'"
    elif isinstance(value, str):
        # 字符串需要转义
        escaped = value.replace("'", "''").replace("\\", "\\\\")
        return f"'{escaped}'"
    elif isinstance(value, bool):
        return '1' if value else '0'
    else:
        return str(value)


def export_to_sql(sqlite_conn, output_file):
    """导出 SQLite 数据为 MySQL 兼容的 SQL 文件"""
    cursor = sqlite_conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📋 发现 {len(tables)} 个表: {', '.join(tables)}\n")
    
    # 确保输出目录存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入文件头
        f.write("-- ============================================\n")
        f.write("-- SQLite to MySQL Migration Script\n")
        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- ============================================\n\n")
        f.write("SET NAMES utf8mb4;\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
        
        total_rows = 0
        
        for table_name in tables:
            print(f"🔄 导出表: {table_name}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # 生成 CREATE TABLE 语句
            f.write(f"-- 表: {table_name}\n")
            f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
            f.write(f"CREATE TABLE `{table_name}` (\n")
            
            col_defs = []
            primary_keys = []
            
            for col in columns:
                cid, name, col_type, notnull, default_value, pk = col
                mysql_type = convert_sqlite_type_to_mysql(col_type)
                
                col_def = f"  `{name}` {mysql_type}"
                
                if notnull:
                    col_def += " NOT NULL"
                
                if default_value is not None:
                    if default_value == 'CURRENT_TIMESTAMP':
                        col_def += f" DEFAULT {default_value}"
                    else:
                        col_def += f" DEFAULT '{default_value}'"
                
                if pk:
                    primary_keys.append(name)
                
                col_defs.append(col_def)
            
            if primary_keys:
                col_defs.append(f"  PRIMARY KEY ({', '.join([f'`{k}`' for k in primary_keys])})")
            
            f.write(",\n".join(col_defs) + "\n")
            f.write(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\n")
            
            # 导出数据
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if rows:
                col_names = [description[0] for description in cursor.description]
                
                f.write(f"-- 数据: {table_name} ({len(rows)} 行)\n")
                f.write(f"INSERT INTO `{table_name}` ({', '.join([f'`{c}`' for c in col_names])}) VALUES\n")
                
                for i, row in enumerate(rows):
                    values = [escape_mysql_value(val) for val in row]
                    line = f"  ({', '.join(values)})"
                    
                    if i < len(rows) - 1:
                        line += ","
                    else:
                        line += ";"
                    
                    f.write(line + "\n")
                
                f.write("\n")
                total_rows += len(rows)
                print(f"  ✅ 导出 {len(rows)} 行")
            else:
                print(f"  ℹ️  无数据")
            
            f.write("\n")
        
        # 写入文件尾
        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")
        
        print(f"\n✅ 导出完成！")
        print(f"   文件: {output_file}")
        print(f"   表数: {len(tables)}")
        print(f"   总行数: {total_rows}")


def import_to_mysql(sql_file):
    """导入 SQL 文件到 MySQL"""
    try:
        import pymysql
    except ImportError:
        print("❌ 缺少 pymysql 依赖，请安装: pip install pymysql")
        return False
    
    mysql_host = os.environ.get("MYSQL_HOST", "localhost")
    mysql_port = int(os.environ.get("MYSQL_PORT", "3306"))
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "")
    mysql_database = os.environ.get("MYSQL_DATABASE", "doculogic")
    
    if not mysql_password:
        print("❌ 请设置 MYSQL_PASSWORD 环境变量")
        print("   示例: export MYSQL_PASSWORD=your_password")
        return False
    
    if not Path(sql_file).exists():
        print(f"❌ SQL 文件不存在: {sql_file}")
        return False
    
    print(f"📊 MySQL 数据库: {mysql_host}:{mysql_port}/{mysql_database}")
    print(f"📄 SQL 文件: {sql_file}")
    print()
    
    try:
        # 连接 MySQL
        conn = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database,
            charset='utf8mb4'
        )
        
        print("✅ MySQL 连接成功")
        
        # 读取 SQL 文件
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 执行 SQL
        cursor = conn.cursor()
        
        # 分割 SQL 语句（按分号分割）
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        print(f"🔄 开始导入... ({len(statements)} 条语句)")
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                success_count += 1
                
                # 每 10 条显示一次进度
                if i % 10 == 0:
                    print(f"  进度: {i}/{len(statements)}")
            except Exception as e:
                error_count += 1
                print(f"  ❌ 错误 (语句 {i}): {str(e)[:100]}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ 导入完成！")
        print(f"   成功: {success_count} 条语句")
        if error_count > 0:
            print(f"   失败: {error_count} 条语句")
        
        return error_count == 0
        
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python migrate_sqlite_to_mysql.py export    # 导出 SQLite 为 SQL 文件")
        print("  python migrate_sqlite_to_mysql.py import    # 导入 SQL 文件到 MySQL")
        print()
        print("示例:")
        print("  # 1. 导出")
        print("  python migrate_sqlite_to_mysql.py export")
        print()
        print("  # 2. 导入（需要设置 MySQL 密码）")
        print("  export MYSQL_PASSWORD=your_password")
        print("  python migrate_sqlite_to_mysql.py import")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "export":
        print("=" * 60)
        print("  SQLite → SQL 导出工具")
        print("=" * 60)
        print()
        
        sqlite_conn = get_sqlite_connection()
        if not sqlite_conn:
            sys.exit(1)
        
        # 固定输出路径：web/data/mysql.sql
        output_file = PROJECT_ROOT / "web" / "data" / "mysql.sql"
        
        try:
            export_to_sql(sqlite_conn, str(output_file))
        finally:
            sqlite_conn.close()
    
    elif command == "import":
        print("=" * 60)
        print("  SQL → MySQL 导入工具")
        print("=" * 60)
        print()
        
        # 使用固定路径：web/data/mysql.sql
        sql_file = PROJECT_ROOT / "web" / "data" / "mysql.sql"
        
        if not sql_file.exists():
            print("❌ 未找到迁移文件，请先执行导出")
            print("   python migrate_sqlite_to_mysql.py export")
            sys.exit(1)
        
        print(f"📄 使用迁移文件: {sql_file}")
        print()
        
        success = import_to_mysql(str(sql_file))
        sys.exit(0 if success else 1)
    
    else:
        print(f"❌ 未知命令: {command}")
        print("   可用命令: export, import")
        sys.exit(1)


if __name__ == "__main__":
    main()
