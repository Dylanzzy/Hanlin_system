import os
import pymysql
from contextlib import contextmanager


class DatabaseConnectionError(Exception):
    pass


def _build_config():
    return {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', '123456'),
        'database': os.getenv('DB_NAME', 'hanlin'),
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
