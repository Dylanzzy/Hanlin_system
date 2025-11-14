"""备用的远程数据库连接工具 (建议与 `db_utils.py` 合并后删除)。

安全改进:
  1. 移除硬编码密碼/IP，改為讀取環境變量。
  2. 提供明確的環境變量名稱（可在 .env 中配置）。
  3. 預設值留空，若未配置將報錯而不是意外連到生產。

使用方式:
  在 .env 或系統環境中設置:
    REMOTE_DB_HOST=106.52.15.205
    REMOTE_DB_PORT=6606
    REMOTE_DB_USER=root
    REMOTE_DB_PASSWORD=***
    REMOTE_DB_NAME=han

  然後:
    from db_utilsn import get_db_connection
    conn, cursor = get_db_connection()
"""

import os
import pymysql
from contextlib import contextmanager


class DatabaseConnectionError(Exception):
    pass


def _build_config():
    host = os.getenv('REMOTE_DB_HOST')
    port = os.getenv('REMOTE_DB_PORT')
    user = os.getenv('REMOTE_DB_USER')
    password = os.getenv('REMOTE_DB_PASSWORD')
    name = os.getenv('REMOTE_DB_NAME')
    if not all([host, port, user, password, name]):
        raise DatabaseConnectionError('遠程資料庫環境變量未完整配置 (REMOTE_DB_*)')
    return {
        'host': host,
        'port': int(port),
        'user': user,
        'password': password,
        'database': name,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': True,
        'connect_timeout': 5,
        'read_timeout': 10,
        'write_timeout': 10,
    }


def get_db_connection():
    try:
        config = _build_config()
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        return conn, cursor
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else None
        msg = str(e)
        hints = []
        if code == 1045:
            hints.append('账号或密码错误 (1045)')
        if code == 1049:
            hints.append('数据库不存在 (1049) - 需要先创建数据库')
        if 'timed out' in msg.lower():
            hints.append('连接超时: 服务未启动 / 防火墙 / 端口不通')
        raise DatabaseConnectionError(f'连接失败 code={code}: {msg}' + (('\n' + '\n'.join(hints)) if hints else '')) from e
    except Exception as e:
        raise DatabaseConnectionError(f'未知数据库错误: {e.__class__.__name__}: {e}') from e


@contextmanager
def db_cursor():
    conn, cursor = None, None
    try:
        conn, cursor = get_db_connection()
        yield conn, cursor
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
