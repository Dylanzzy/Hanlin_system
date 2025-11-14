from flask import Flask, send_from_directory, request, jsonify, send_file, after_this_request, Response
from flask_cors import CORS
from db_utils import get_db_connection, DatabaseConnectionError
import os
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import quote
try:
    import pandas as pd
    PANDAS_IMPORT_ERROR = None
except Exception as _pe:  # 不讓主進程啟動失敗
    pd = None
    PANDAS_IMPORT_ERROR = f"pandas 無法導入: {_pe}"
from werkzeug.utils import secure_filename, safe_join
try:  # 安全防護，不影響主流程
    import numpy as _np  # noqa: F401
    if not hasattr(_np, 'float'):
        _np.float = float  # type: ignore[attr-defined]
    if not hasattr(_np, 'int'):
        _np.int = int  # type: ignore[attr-defined]
    if not hasattr(_np, 'bool'):
        _np.bool = bool  # type: ignore[attr-defined]
except Exception:
    pass
import unicodedata, mimetypes

UPLOAD_BASE = os.path.join(os.getcwd(), 'uploads', 'photos')
os.makedirs(UPLOAD_BASE, exist_ok=True)
ALLOWED_IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
EXPORT_DIR = os.path.join(os.getcwd(), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# 当导出文件数量达到或超过阈值时清空目录（含子项目仅文件）
EXPORT_MAX_FILES = int(os.getenv('EXPORT_MAX_FILES', '5'))  # 可通過環境變量調整，默認 5

def _purge_exports_if_limit():
    try:
        entries = [f for f in os.listdir(EXPORT_DIR) if os.path.isfile(os.path.join(EXPORT_DIR, f))]
        if len(entries) >= EXPORT_MAX_FILES:
            for f in entries:
                fp = os.path.join(EXPORT_DIR, f)
                try:
                    os.remove(fp)
                except Exception:
                    pass
            return True, len(entries)
        return False, len(entries)
    except Exception:
        return False, -1

app = Flask(__name__, static_folder="dist")
CORS(app)


@app.route("/api/progress", methods=["GET"])
def get_progress():
    conn = None
    cursor = None
    try:
        # 获取数据库连接
        conn, cursor = get_db_connection()

        # 解析请求参数
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=100, type=int)
        search = request.args.get('search', default=None, type=str)
        all_flag = request.args.get('all', default='false') == 'true'
        print(f"Request params - page: {page}, limit: {limit}, search: {search}, all: {all_flag}")

        # 构建查询：进度表并左连接教学记录统计（仅统计 teaching_type 包含 '正式交付' 的记录）
        sql = (
            "SELECT "
            "p.*, "
            "ROUND(tr_stats.avg_teaching_score, 2) as avg_teaching_score, "
            "tr_stats.teaching_type_count "
            "FROM progress p "
            "LEFT JOIN ("
            "    SELECT "
            "        course_name, "
            "        AVG(teaching_score) as avg_teaching_score, "
            "        COUNT(DISTINCT teaching_type) as teaching_type_count "
            "    FROM teaching_record "
            "    WHERE teaching_type LIKE '%%正式交付%%' "
            "    GROUP BY course_name"
            ") tr_stats ON p.courseName = tr_stats.course_name"
        )
        count_sql = "SELECT COUNT(*) AS total FROM progress"
        params = []
        conditions = []

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                "(courseName LIKE %s OR dri LIKE %s OR responsible LIKE %s "
                "OR developer LIKE %s OR progress LIKE %s)"
            )
            params.extend([search_pattern] * 5)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            count_sql += " WHERE " + " AND ".join(conditions)

        # 全量数据或分页查询
        if all_flag:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            total = len(rows)
        else:
            offset = (page - 1) * limit
            cursor.execute(sql + " LIMIT %s OFFSET %s", params + [limit, offset])
            rows = cursor.fetchall()
            
            # 获取总数
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

        return jsonify({
            "success": True,
            "data": rows,
            "total": total,
            "pagination": {
                "current": page,
                "pageSize": limit,
                "totalPages": (total + limit - 1) // limit
            } if not all_flag else None
        })

    except DatabaseConnectionError as e:
        return jsonify({
            "success": False,
            "message": "数据库操作失败",
            "error": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "请求处理失败",
            "error": str(e)
        }), 500
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


@app.route('/api/progress/template', methods=['GET'])
def progress_export_template():
    if pd is None:
        return jsonify({'success': False, 'message': 'pandas 未安裝，請先執行: pip install pandas xlsxwriter', 'detail': PANDAS_IMPORT_ERROR}), 500
    # 選擇引擎
    engine = None
    try:
        import xlsxwriter  # noqa: F401
        engine = 'xlsxwriter'
    except Exception:
        try:
            import openpyxl  # noqa: F401
            engine = 'openpyxl'
        except Exception:
            return jsonify({'success': False, 'message': '缺少可用的 Excel 寫入引擎，請安裝: pip install xlsxwriter (推薦) 或 pip install openpyxl'}), 500

    conn = cursor = None
    try:
        conn, cursor = get_db_connection()

        def fetch_df(table_name):
            try:
                cursor.execute("SHOW TABLES LIKE %s", [table_name])
                if not cursor.fetchone():
                    return None
                cursor.execute(f"DESCRIBE `{table_name}`")
                cols = [r['Field'] for r in cursor.fetchall()]
                cursor.execute(f"SELECT * FROM `{table_name}`")
                rows = cursor.fetchall()
                # pandas 會將 None 轉為 NaN；這裡按需求可保持 None
                df = pd.DataFrame(rows, columns=cols)
                return (table_name, df)
            except Exception:
                return None

        sheets = []
        for name in ['progress', 'teacher_details', 'teaching_record']:
            result = fetch_df(name)
            if result:
                sheets.append(result)
        if not sheets:
            return jsonify({'success': False, 'message': '數據庫中未找到相關表 (progress/teacher_details/teaching_record)'}), 404

        bio = BytesIO()
        with pd.ExcelWriter(bio, engine=engine) as writer:
            for sheet_name, df in sheets:
                safe_name = sheet_name[:31]
                df.to_excel(writer, index=False, sheet_name=safe_name)
                # 自適應列寬 (僅對 xlsxwriter 寫入進行處理)
                try:
                    if engine == 'xlsxwriter':
                        worksheet = writer.sheets[safe_name]
                        for idx, col in enumerate(df.columns):
                            series = df[col].astype(str).fillna('')
                            max_len = max([len(col)] + [len(v.encode('utf-8')) // 2 + len(v) // 2 for v in series])
                            worksheet.set_column(idx, idx, min(60, max(10, max_len + 2)))
                except Exception:
                    pass
        bio.seek(0)
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"進度模板_{ts}.xlsx"
        # 使用 RFC 5987 filename* 方式保留 UTF-8 中文，並同時提供 ASCII fallback
        response = send_file(
            bio,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        try:
            # werkzeug 會自動生成一個 Content-Disposition，我們覆蓋為雙參數版本
            quoted = quote(filename)
            # filename 提供原始（可能被某些瀏覽器回退處理），filename* 提供 UTF-8 編碼版本
            response.headers['Content-Disposition'] = f"attachment; filename=_{ts}.xlsx; filename*=UTF-8''{quoted}"
        except Exception:
            pass
        return response
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '數據庫連接失敗', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '生成模板失敗', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/progress/import', methods=['POST'])
def progress_import():
    """多表導入：支持單 sheet (progress) 或多 sheet (progress/teacher_details/teaching_record)。
    Excel: 三個 sheet 名對應三個表；CSV 仍僅支持 progress。
    對所有插入/更新自動寫入或更新 `Update_time = NOW()`；若資料表缺少該列會自動添加。
    行處理策略：
      - 若存在 id 且有值：嘗試 UPDATE，若未命中則 INSERT (包含該 id)
      - 否則直接 INSERT
      - 整行（除 id 外）全為空則跳過
    回傳 stats 按表分類。
    """
    if pd is None:
        return jsonify({'success': False, 'message': 'pandas 未安裝，請先安裝後再導入'}), 500
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({'success': False, 'message': '缺少上傳文件 file'}), 400
    filename = upload.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {'.xlsx', '.csv'}:
        return jsonify({'success': False, 'message': '文件格式不支持，僅支持 .xlsx 或 .csv'}), 400
    # 讀取原始位元
    raw = upload.read()
    if not raw:
        return jsonify({'success': False, 'message': '文件為空'}), 400
    if len(raw) > 10 * 1024 * 1024:
        return jsonify({'success': False, 'message': '文件超過 10MB 限制'}), 400

    # 解析為 DataFrame 或 sheet->DataFrame 映射
    sheets_map = {}
    try:
        if ext == '.xlsx':
            # openpyxl 版本檢查（pandas 讀取 xlsx 需要 >=3.1.0）
            try:
                import openpyxl  # noqa: F401
                from packaging import version
                if version.parse(openpyxl.__version__) < version.parse('3.1.0'):
                    return jsonify({'success': False, 'message': 'openpyxl 版本過舊，請升級至 >=3.1.0', 'currentVersion': openpyxl.__version__, 'upgrade': 'pip install --upgrade openpyxl'}), 500
            except ImportError:
                return jsonify({'success': False, 'message': '未安裝 openpyxl，請先: pip install openpyxl>=3.1.0'}), 500
            try:
                # sheet_name=None 讀取全部 sheet
                all_sheets = pd.read_excel(BytesIO(raw), sheet_name=None, dtype=str)
            except Exception as e:
                return jsonify({'success': False, 'message': '解析 Excel 失敗', 'error': str(e)}), 400
            # 過濾只保留需要的三個表名 (大小寫敏感按原樣)
            for target in ['progress', 'teacher_details', 'teaching_record']:
                if target in all_sheets:
                    sheets_map[target] = all_sheets[target]
            # 若沒有任何匹配 sheet，兼容舊格式：如果只有一個 sheet，當作 progress
            if not sheets_map and all_sheets:
                if len(all_sheets) == 1:
                    only_name, only_df = next(iter(all_sheets.items()))
                    sheets_map['progress'] = only_df
            if not sheets_map:
                return jsonify({'success': False, 'message': '未找到期望的 sheet: progress / teacher_details / teaching_record'}), 400
        else:  # CSV -> 只映射 progress
            csv_df = None
            for enc in ['utf-8-sig', 'utf-8', 'gbk', 'cp936']:
                try:
                    txt = raw.decode(enc)
                    csv_df = pd.read_csv(BytesIO(txt.encode('utf-8')), dtype=str)
                    break
                except Exception:
                    continue
            if csv_df is None:
                return jsonify({'success': False, 'message': 'CSV 解析失敗，請確認編碼 (建議 UTF-8)'}), 400
            sheets_map['progress'] = csv_df
    except Exception as e:
        return jsonify({'success': False, 'message': '文件解析階段失敗', 'error': str(e)}), 400

    # 數據庫連接
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()

        def ensure_update_time_column(table_name: str):
            try:
                cursor.execute(f"DESCRIBE `{table_name}`")
                cols = [r['Field'] for r in cursor.fetchall()]
                if 'Update_time' not in cols:
                    cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `Update_time` DATETIME NULL")
                    conn.commit()
            except Exception:
                pass

        def import_one_table(table_name: str, df):
            # 前置清理
            df = df.copy()
            df.dropna(how='all', inplace=True)
            if df.empty:
                return {'totalRows': 0, 'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0, 'usedColumns': [], 'hasIdColumn': False, 'message': '無有效數據'}
            if len(df) > 5000:
                return {'totalRows': int(len(df)), 'inserted': 0, 'updated': 0, 'skipped': 0, 'invalid': 0, 'usedColumns': [], 'hasIdColumn': False, 'message': '超出 5000 行限制'}
            # 表結構
            try:
                cursor.execute(f"DESCRIBE `{table_name}`")
            except Exception:
                return {'totalRows': int(len(df)), 'inserted': 0, 'updated': 0, 'skipped': int(len(df)), 'invalid': 0, 'usedColumns': [], 'hasIdColumn': False, 'message': '資料表不存在'}
            columns_info = cursor.fetchall()
            table_columns = [c['Field'] for c in columns_info]
            ensure_update_time_column(table_name)
            # 重新獲取（可能多了 Update_time）
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns_info = cursor.fetchall()
            table_columns = [c['Field'] for c in columns_info]
            df.columns = [str(c).strip() for c in df.columns]
            usable_cols = [c for c in df.columns if c in table_columns and c != 'Update_time']
            if not usable_cols:
                return {'totalRows': int(len(df)), 'inserted': 0, 'updated': 0, 'skipped': int(len(df)), 'invalid': 0, 'usedColumns': [], 'hasIdColumn': False, 'message': '無匹配欄位'}
            has_id = 'id' in usable_cols
            inserted = updated = skipped = invalid = 0
            for _, row in df.iterrows():
                row_data = row.to_dict()
                clean = {}
                for k in usable_cols:
                    v = row_data.get(k)
                    if pd.isna(v):
                        v = None
                    if isinstance(v, str):
                        v = v.strip()
                    clean[k] = v
                if not any(v not in (None, '') for k, v in clean.items() if k != 'id'):
                    skipped += 1
                    continue
                try:
                    if has_id and clean.get('id') not in (None, ''):
                        update_cols = [c for c in usable_cols if c != 'id']
                        set_parts = [f"{c}=%s" for c in update_cols]
                        set_parts.append("Update_time=NOW()")
                        params = [clean[c] for c in update_cols]
                        params.append(clean['id'])
                        cursor.execute(f"UPDATE `{table_name}` SET {', '.join(set_parts)} WHERE id=%s", params)
                        if cursor.rowcount == 0:
                            # 插入包含 id
                            insert_cols = [c for c in usable_cols if clean.get(c) not in (None, '')]
                            insert_cols.append('Update_time')
                            placeholders = ','.join(['%s'] * (len(insert_cols)-1) + ['NOW()'])
                            value_params = [clean[c] for c in insert_cols if c != 'Update_time']
                            cursor.execute(f"INSERT INTO `{table_name}` ({','.join(insert_cols)}) VALUES ({placeholders})", value_params)
                            inserted += 1
                        else:
                            updated += 1
                    else:
                        insert_cols = [c for c in usable_cols if c != 'id' and clean.get(c) not in (None, '')]
                        if not insert_cols:
                            skipped += 1
                            continue
                        insert_cols.append('Update_time')
                        placeholders = ','.join(['%s'] * (len(insert_cols)-1) + ['NOW()'])
                        value_params = [clean[c] for c in insert_cols if c != 'Update_time']
                        cursor.execute(f"INSERT INTO `{table_name}` ({','.join(insert_cols)}) VALUES ({placeholders})", value_params)
                        inserted += 1
                except Exception:
                    invalid += 1
                    continue
            return {
                'totalRows': int(len(df)),
                'inserted': inserted,
                'updated': updated,
                'skipped': skipped,
                'invalid': invalid,
                'usedColumns': usable_cols,
                'hasIdColumn': has_id
            }

        overall_stats = {}
        for tbl, frame in sheets_map.items():
            overall_stats[tbl] = import_one_table(tbl, frame)
        conn.commit()
        return jsonify({'success': True, 'message': '多表導入完成', 'stats': overall_stats})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '數據庫連接失敗', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '導入處理失敗', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/progress/update_time', methods=['GET'])
def progress_update_time():
    """獲取 progress / teacher_details / teaching_record 三個表的最近 Update_time。
    回傳格式:
    {
      success: true,
      data: { progress: '2025-09-27 12:00:00', teacher_details: '...', teaching_record: '...' },
      latest: '2025-09-27 12:05:11'
    }
    若表/列不存在則跳過。"""
    conn = cursor = None
    tables = ['progress', 'teacher_details', 'teaching_record']
    per_table = {}
    latest_dt = None
    try:
        conn, cursor = get_db_connection()
        for tbl in tables:
            try:
                cursor.execute("SHOW TABLES LIKE %s", [tbl])
                if not cursor.fetchone():
                    continue
                cursor.execute(f"SHOW COLUMNS FROM `{tbl}` LIKE 'Update_time'")
                if not cursor.fetchone():  # 沒有列
                    continue
                cursor.execute(f"SELECT MAX(Update_time) AS latest FROM `{tbl}`")
                row = cursor.fetchone()
                if row and row.get('latest'):
                    val = row['latest']
                    # val 可能是 datetime 或 字串
                    if isinstance(val, datetime):
                        formatted = val.strftime('%Y-%m-%d %H:%M:%S')
                        dt_obj = val
                    else:
                        formatted = str(val)
                        try:
                            dt_obj = datetime.strptime(formatted, '%Y-%m-%d %H:%M:%S')
                        except Exception:
                            dt_obj = None
                    per_table[tbl] = formatted
                    if dt_obj and (latest_dt is None or dt_obj > latest_dt):
                        latest_dt = dt_obj
            except Exception:
                continue
        return jsonify({
            'success': True,
            'data': per_table,
            'latest': latest_dt.strftime('%Y-%m-%d %H:%M:%S') if latest_dt else None
        })
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '數據庫連接失敗', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '獲取更新時間失敗', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


# ---------------- Lecture APIs (migrated from Node LectureController) ----------------

def _lecture_base_select():
    # 使用双百分号避免 Python 对 %Y %m 等进行格式化解析
    return ("SELECT id, DATE_FORMAT(applicationDate, '%%Y-%%m-%%d %%H:%%i:%%s') as applicationDate, "
            "applicant, employeeId, department, course, area, shift, "
            "DATE_FORMAT(lectureDate, '%%Y-%%m-%%d %%H:%%i:%%s') as lectureDate, score, result FROM lecture")


@app.route('/api/Lecture', methods=['GET'])
@app.route('/api/Lecture/all', methods=['GET'])
def lecture_get_all():
    all_flag = request.path.endswith('/all') or request.args.get('all') == 'true'
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=100, type=int)
    search = request.args.get('search', default=None, type=str)
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        base_sql = _lecture_base_select()
        count_sql = 'SELECT COUNT(*) as total FROM lecture'
        where_clauses = []
        params = []
        if search:
            # 增加戰區(area)、棒次(shift) 搜索
            where_clauses.append('(applicant LIKE %s OR course LIKE %s OR department LIKE %s OR employeeId LIKE %s OR area LIKE %s OR shift LIKE %s)')
            like = f"%{search}%"
            params.extend([like, like, like, like, like, like])
        if where_clauses:
            where_sql = ' WHERE ' + ' AND '.join(where_clauses)
            base_sql += where_sql
            count_sql += where_sql
        base_sql += ' ORDER BY applicationDate DESC'
        if all_flag:
            cursor.execute(base_sql, params)
            rows = cursor.fetchall()
            return jsonify({'success': True, 'data': rows, 'total': len(rows)})
        offset = (page - 1) * limit
        cursor.execute(base_sql + ' LIMIT %s OFFSET %s', params + [limit, offset])
        rows = cursor.fetchall()
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        return jsonify({
            'success': True,
            'data': rows,
            'pagination': {
                'current': page,
                'pageSize': limit,
                'total': total,
                'totalPages': (total + limit - 1) // limit
            }
        })
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture/<int:record_id>', methods=['GET'])
def lecture_get_by_id(record_id):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE id = %s', [record_id])
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': '未找到指定的培训记录'}), 404
        return jsonify({'success': True, 'data': row})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture/applicant/<string:name>', methods=['GET'])
def lecture_get_by_applicant(name):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE applicant LIKE %s', [f'%{name}%'])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture/result/<string:result>', methods=['GET'])
def lecture_get_by_result(result):
    valid_results = ['未通過', '儲備講師']
    if result not in valid_results:
        return jsonify({'success': False, 'message': '无效的结果状态，只能是：未通過、儲備講師'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE result = %s', [result])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture/department/<string:department>', methods=['GET'])
def lecture_get_by_department(department):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE department LIKE %s', [f'%{department}%'])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

@app.route('/api/Lecture/area/<string:area>', methods=['GET'])
def lecture_get_by_area(area):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE area LIKE %s', [f'%{area}%'])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

@app.route('/api/Lecture/shift/<string:shift>', methods=['GET'])
def lecture_get_by_shift(shift):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE shift = %s', [shift])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

@app.route('/api/Lecture/stats', methods=['GET'])
def lecture_stats():
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('SELECT COUNT(*) as total FROM lecture')
        total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as passed FROM lecture WHERE result = '通过'")
        passed = cursor.fetchone()['passed']
        cursor.execute("SELECT COUNT(*) as failed FROM lecture WHERE result = '失败'")
        failed = cursor.fetchone()['failed']
        cursor.execute("SELECT department, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM lecture GROUP BY department")
        departments = cursor.fetchall()
        cursor.execute("SELECT course, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM lecture GROUP BY course")
        courses = cursor.fetchall()
        # 新增戰區/棒次統計（若表中存在對應數據）
        try:
            cursor.execute("SELECT area, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM lecture WHERE area IS NOT NULL GROUP BY area")
            areas = cursor.fetchall()
        except Exception:
            areas = []
        try:
            cursor.execute("SELECT shift, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM lecture WHERE shift IS NOT NULL GROUP BY shift")
            shifts = cursor.fetchall()
        except Exception:
            shifts = []
        pass_rate = f"{(passed / total * 100):.2f}" if total else '0'
        return jsonify({'success': True, 'data': {
            'overview': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'passRate': pass_rate
            },
            'departments': departments,
            'courses': courses,
            'areas': areas,
            'shifts': shifts
        }})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取统计信息失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture', methods=['POST'])
def lecture_create():
    data = request.get_json(force=True, silent=True) or {}
    # 增加戰區、棒次必填
    required = ['applicationDate', 'applicant', 'employeeId', 'department', 'course', 'area', 'shift']
    missing = [f for f in required if data.get(f) in (None, '')]
    if missing:
        return jsonify({'success': False, 'message': '缺少必填字段', 'required': required, 'missing': missing}), 400
    result_value = data.get('result')
    if result_value and result_value not in ['未通過', '儲備講師']:
        return jsonify({'success': False, 'message': '无效的结果状态，只能是：未通過、儲備講師'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = ('INSERT INTO lecture (applicationDate, applicant, employeeId, department, course, area, shift, lectureDate, score, result) '
               'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
        cursor.execute(sql, [
            data.get('applicationDate'),
            data.get('applicant'),
            data.get('employeeId'),
            data.get('department'),
            data.get('course'),
            data.get('area'),
            data.get('shift'),
            data.get('lectureDate'),
            data.get('score'),
            result_value
        ])
        new_id = cursor.lastrowid
        cursor.execute(_lecture_base_select() + ' WHERE id = %s', [new_id])
        row = cursor.fetchone()
        return jsonify({'success': True, 'message': '培训记录创建成功', 'data': row}), 201
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        # PyMySQL 重复键错误 code=1062
        if hasattr(e, 'args') and e.args and e.args[0] == 1062:
            return jsonify({'success': False, 'message': '记录已存在，可能重复'}), 409
        return jsonify({'success': False, 'message': '创建培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture/<int:record_id>', methods=['PUT'])
def lecture_update(record_id):
    data = request.get_json(force=True, silent=True) or {}
    result_value = data.get('result')
    if result_value and result_value not in ['未通過', '儲備講師']:
        return jsonify({'success': False, 'message': '无效的结果状态，只能是：未通過、儲備講師'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE id = %s', [record_id])
        existing = cursor.fetchone()
        if not existing:
            return jsonify({'success': False, 'message': '未找到指定的培训记录'}), 404
        # 动态构建更新
        fields = []
        values = []
        # 允許更新 area / shift
        allowed = ['applicationDate','applicant','employeeId','department','course','area','shift','lectureDate','score','result']
        for k in allowed:
            if k in data:
                fields.append(f"{k}=%s")
                values.append(data.get(k))
        if not fields:
            return jsonify({'success': False, 'message': '没有提供要更新的字段'}), 400
        values.append(record_id)
        sql = f"UPDATE lecture SET {', '.join(fields)} WHERE id=%s"
        cursor.execute(sql, values)
        cursor.execute(_lecture_base_select() + ' WHERE id = %s', [record_id])
        updated = cursor.fetchone()
        return jsonify({'success': True, 'message': '培训记录更新成功', 'data': updated})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '更新培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Lecture/<int:record_id>', methods=['DELETE'])
def lecture_delete(record_id):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_lecture_base_select() + ' WHERE id = %s', [record_id])
        existing = cursor.fetchone()
        if not existing:
            return jsonify({'success': False, 'message': '未找到指定的培训记录'}), 404
        cursor.execute('DELETE FROM lecture WHERE id = %s', [record_id])
        return jsonify({'success': True, 'message': '培训记录删除成功', 'data': {'deletedRecord': existing}})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '删除培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


# ---------------- Incubation APIs (migrated) ----------------

def _incubation_base_select():
    return ("SELECT id, DATE_FORMAT(applicationDate, '%%Y-%%m-%%d %%H:%%i:%%s') as applicationDate, "
            "applicant, employeeId, department, course, DATE_FORMAT(lectureDate, '%%Y-%%m-%%d %%H:%%i:%%s') as lectureDate, "
            "score, result, area, shift FROM incubation")


@app.route('/api/Incubation', methods=['GET'])
@app.route('/api/Incubation/all', methods=['GET'])
def incubation_get_all():
    all_flag = request.path.endswith('/all') or request.args.get('all') == 'true'
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=100, type=int)
    search = request.args.get('search', default=None, type=str)
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        base_sql = _incubation_base_select()
        count_sql = 'SELECT COUNT(*) as total FROM incubation'
        where_clauses = []
        params = []
        if search:
            where_clauses.append('(applicant LIKE %s OR course LIKE %s OR department LIKE %s OR employeeId LIKE %s OR area LIKE %s)')
            like = f"%{search}%"
            params.extend([like, like, like, like, like])
        if where_clauses:
            where_sql = ' WHERE ' + ' AND '.join(where_clauses)
            base_sql += where_sql
            count_sql += where_sql
        base_sql += ' ORDER BY applicationDate DESC'
        if all_flag:
            cursor.execute(base_sql, params)
            rows = cursor.fetchall()
            return jsonify({'success': True, 'data': rows, 'total': len(rows)})
        offset = (page - 1) * limit
        cursor.execute(base_sql + ' LIMIT %s OFFSET %s', params + [limit, offset])
        rows = cursor.fetchall()
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        return jsonify({'success': True, 'data': rows, 'pagination': {
            'current': page,
            'pageSize': limit,
            'total': total,
            'totalPages': (total + limit - 1) // limit
        }})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/<int:record_id>', methods=['GET'])
def incubation_get_by_id(record_id):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE id = %s', [record_id])
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': '未找到指定的培训记录'}), 404
        return jsonify({'success': True, 'data': row})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/applicant/<string:name>', methods=['GET'])
def incubation_get_by_applicant(name):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE applicant LIKE %s', [f'%{name}%'])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/result/<string:result>', methods=['GET'])
def incubation_get_by_result(result):
    valid_results = ['種子講師', '儲備講師','優質講師','金牌講師']
    if result not in valid_results:
        return jsonify({'success': False, 'message': '无效的结果状态，只能是：種子講師 或 儲備講師 或 優質講師 或 金牌講師'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE result = %s', [result])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/department/<string:department>', methods=['GET'])
def incubation_get_by_department(department):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE department LIKE %s', [f'%{department}%'])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/area/<string:area>', methods=['GET'])
def incubation_get_by_area(area):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE area LIKE %s', [f'%{area}%'])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '按片区查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/shift/<string:shift>', methods=['GET'])
def incubation_get_by_shift(shift):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE shift = %s', [shift])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows)})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '按梯次查询培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/stats', methods=['GET'])
def incubation_stats():
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('SELECT COUNT(*) as total FROM incubation')
        total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as passed FROM incubation WHERE result = '通过'")
        passed = cursor.fetchone()['passed']
        cursor.execute("SELECT COUNT(*) as failed FROM incubation WHERE result = '失败'")
        failed = cursor.fetchone()['failed']
        cursor.execute("SELECT department, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM incubation GROUP BY department")
        departments = cursor.fetchall()
        cursor.execute("SELECT course, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM incubation GROUP BY course")
        courses = cursor.fetchall()
        cursor.execute("SELECT area, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM incubation WHERE area IS NOT NULL GROUP BY area")
        areas = cursor.fetchall()
        cursor.execute("SELECT shift, COUNT(*) as total, SUM(result = '通过') as passed, SUM(result = '失败') as failed FROM incubation WHERE shift IS NOT NULL GROUP BY shift")
        shifts = cursor.fetchall()
        pass_rate = f"{(passed / total * 100):.2f}" if total else '0'
        return jsonify({'success': True, 'data': {
            'overview': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'passRate': pass_rate
            },
            'departments': departments,
            'courses': courses,
            'areas': areas,
            'shifts': shifts
        }})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取统计信息失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/applicant-name-options', methods=['GET'])
def incubation_result_options():
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute("SELECT DISTINCT applicant FROM lecture WHERE result != '未通過' ORDER BY applicant ASC")
        rows = cursor.fetchall()
        options = [{'label': r['applicant'], 'value': r['applicant']} for r in rows]
        return jsonify({'Options': options})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取课程名称选项失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation', methods=['POST'])
def incubation_create():
    data = request.get_json(force=True, silent=True) or {}
    required = ['applicationDate', 'applicant', 'employeeId', 'department', 'course']
    missing = [f for f in required if data.get(f) in (None, '')]
    if missing:
        return jsonify({'success': False, 'message': '缺少必填字段', 'required': required, 'missing': missing}), 400
    result_value = data.get('result')
    if result_value and result_value not in ['種子講師', '儲備講師','優質講師','金牌講師']:
        return jsonify({'success': False, 'message': '无效的结果状态，只能是：種子講師 或 儲備講師 或 優質講師 或 金牌講師'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = ('INSERT INTO incubation (applicationDate, applicant, employeeId, department, course, lectureDate, score, result, area, shift) '
               'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
        cursor.execute(sql, [
            data.get('applicationDate'),
            data.get('applicant'),
            data.get('employeeId'),
            data.get('department'),
            data.get('course'),
            data.get('lectureDate'),
            data.get('score'),
            result_value,
            data.get('area'),
            data.get('shift')
        ])
        new_id = cursor.lastrowid
        cursor.execute(_incubation_base_select() + ' WHERE id = %s', [new_id])
        row = cursor.fetchone()
        return jsonify({'success': True, 'message': '培训记录创建成功', 'data': row}), 201
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        if hasattr(e, 'args') and e.args and e.args[0] == 1062:
            return jsonify({'success': False, 'message': '记录已存在，可能重复'}), 409
        return jsonify({'success': False, 'message': '创建培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/<int:record_id>', methods=['PUT'])
def incubation_update(record_id):
    data = request.get_json(force=True, silent=True) or {}
    result_value = data.get('result')
    if result_value and result_value not in ['種子講師', '儲備講師','優質講師','金牌講師']:
        return jsonify({'success': False, 'message': '无效的结果状态，只能是：種子講師 或 儲備講師 或 優質講師 或 金牌講師'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE id = %s', [record_id])
        existing = cursor.fetchone()
        if not existing:
            return jsonify({'success': False, 'message': '未找到指定的培训记录'}), 404
        fields = []
        values = []
        allowed = ['applicationDate','applicant','employeeId','department','course','lectureDate','score','result','area','shift']
        for k in allowed:
            if k in data:
                fields.append(f"{k}=%s")
                values.append(data.get(k))
        if not fields:
            return jsonify({'success': False, 'message': '没有提供要更新的字段'}), 400
        values.append(record_id)
        sql = f"UPDATE incubation SET {', '.join(fields)} WHERE id=%s"
        cursor.execute(sql, values)
        cursor.execute(_incubation_base_select() + ' WHERE id = %s', [record_id])
        updated = cursor.fetchone()
        return jsonify({'success': True, 'message': '培训记录更新成功', 'data': updated})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '更新培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/<int:record_id>', methods=['DELETE'])
def incubation_delete(record_id):
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute(_incubation_base_select() + ' WHERE id = %s', [record_id])
        existing = cursor.fetchone()
        if not existing:
            return jsonify({'success': False, 'message': '未找到指定的培训记录'}), 404
        cursor.execute('DELETE FROM incubation WHERE id = %s', [record_id])
        return jsonify({'success': True, 'message': '培训记录删除成功', 'data': {'deletedRecord': existing}})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '删除培训记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/Incubation/fix-table', methods=['POST'])
def incubation_fix_table():
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('DESCRIBE incubation')
        structure = cursor.fetchall()
        id_field = next((c for c in structure if c['Field'] == 'id'), None)
        actions = []
        # 获取当前最大 id
        cursor.execute('SELECT IFNULL(MAX(id), 0) as maxId FROM incubation')
        max_id = cursor.fetchone()['maxId']
        if not id_field or 'auto_increment' not in (id_field.get('Extra') or ''):
            # 删除主键（如果存在）
            try:
                cursor.execute('ALTER TABLE incubation DROP PRIMARY KEY')
                actions.append('删除原有主键')
            except Exception:
                pass
            cursor.execute('ALTER TABLE incubation MODIFY COLUMN id INT AUTO_INCREMENT PRIMARY KEY')
            actions.append('设置 id 为 AUTO_INCREMENT 主键')
            if max_id > 0:
                cursor.execute(f'ALTER TABLE incubation AUTO_INCREMENT = {max_id + 1}')
                actions.append(f'设置 AUTO_INCREMENT = {max_id + 1}')
        # 确保 area / shift 字段存在
        field_names = {c['Field'] for c in structure}
        if 'area' not in field_names:
            cursor.execute('ALTER TABLE incubation ADD COLUMN area VARCHAR(100) NULL')
            actions.append('添加 area 字段')
        if 'shift' not in field_names:
            cursor.execute('ALTER TABLE incubation ADD COLUMN shift VARCHAR(100) NULL')
            actions.append('添加 shift 字段')
        cursor.execute('DESCRIBE incubation')
        new_structure = cursor.fetchall()
        cursor.execute("SHOW TABLE STATUS LIKE 'incubation'")
        table_status = cursor.fetchone()
        return jsonify({'success': True, 'message': 'incubation 数据库表结构修复完成', 'data': {
            'fixActions': actions if actions else ['表结构已正确，无需修复'],
            'beforeStructure': structure,
            'afterStructure': new_structure,
            'autoIncrementValue': table_status.get('Auto_increment')
        }})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '修复 incubation 数据库表结构失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


# ---------------- Teaching Record APIs (migrated) ----------------

@app.route('/api/teaching-record/line_coursename', methods=['GET'])
def teaching_record_line():
    course_name_value = request.args.get('course_name_value')
    export_csv = request.args.get('export_csv') == 'true'
    if not course_name_value:
        return jsonify({'success': False, 'message': '缺少必需参数 course_name_value'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        # sql = (
        #     "SELECT teaching_type, ROUND(AVG(teaching_score), 2) AS avg_score, COUNT(*) AS record_count, "
        #     "GROUP_CONCAT(CONCAT(name, ':', teaching_score) ORDER BY CAST(SUBSTRING(teaching_type, "
        #     "CASE WHEN teaching_type LIKE '試點%%' THEN 3 WHEN teaching_type LIKE '試跑%%' THEN 3 WHEN teaching_type LIKE '正式交付%%' THEN 5 END) AS UNSIGNED)) AS details "
        #     "FROM teaching_record WHERE course_name = %s GROUP BY teaching_type ORDER BY CASE "
        #     "WHEN teaching_type LIKE '試點%%' THEN 1 WHEN teaching_type LIKE '試跑%%' THEN 2 WHEN teaching_type LIKE '正式交付%%' THEN 3 ELSE 4 END, "
        #     "CAST(SUBSTRING(teaching_type, CASE WHEN teaching_type LIKE '試點%%' THEN 3 WHEN teaching_type LIKE '試跑%%' THEN 3 WHEN teaching_type LIKE '正式交付%%' THEN 5 ELSE 1 END) AS UNSIGNED) ASC"
        # )
        # sql = (
        #     """
        #     SELECT teaching_type, teaching_factory, ROUND(AVG(teaching_score), 2) AS avg_score, COUNT(*) AS record_count, GROUP_CONCAT(CONCAT(name, ':', teaching_score) 
        #     ORDER BY CAST(SUBSTRING(teaching_type, CASE WHEN teaching_type LIKE '試點%%' THEN 3 WHEN teaching_type LIKE '試跑%%' THEN 3 WHEN teaching_type LIKE '正式交付%%' THEN 5 END) AS UNSIGNED)) AS details, 
        #     CONCAT(REGEXP_SUBSTR(teaching_type, '^[^0-9]+'), CASE teaching_factory WHEN '觀瀾' THEN 'GL' WHEN '晉城' THEN 'JC' WHEN '太原' THEN 'TY' WHEN '綜保區' THEN 'ZZC' WHEN '濟源' THEN 'JY' WHEN '加工區' THEN 'ZZK' WHEN '蘭考' THEN 'LK' WHEN '龍華' THEN 'LH' WHEN '鶴壁' THEN 'HB' ELSE '' END, 
        #     REGEXP_SUBSTR(teaching_type, '[0-9]+$')) AS new_teaching_type FROM teaching_record WHERE course_name = %s GROUP BY teaching_type, teaching_factory ORDER BY CASE WHEN teaching_type LIKE '試點%%' THEN 1 WHEN teaching_type LIKE '試跑%%' THEN 2 WHEN teaching_type LIKE '正式交付%%' THEN 3 ELSE 4 END, 
        #     CAST(SUBSTRING(teaching_type, CASE WHEN teaching_type LIKE '試點%%' THEN 3 WHEN teaching_type LIKE '試跑%%' THEN 3 WHEN teaching_type LIKE '正式交付%%' THEN 5 ELSE 1 END) AS UNSIGNED) ASC
        #     """
        #     )
        sql = (
            """
                SELECT 
                    teaching_type, 
                    teaching_factory, 
                    ROUND(AVG(teaching_score), 2) AS avg_score, 
                    COUNT(*) AS record_count, 
                    GROUP_CONCAT(CONCAT(name, ':', teaching_score)
                        ORDER BY CAST(SUBSTRING(teaching_type, 
                            CASE 
                                WHEN teaching_type LIKE '試點%%' THEN 3 
                                WHEN teaching_type LIKE '試跑%%' THEN 3 
                                WHEN teaching_type LIKE '正式交付%%' THEN 5 
                            END) AS UNSIGNED)) AS details
                FROM teaching_record 
                WHERE course_name = %s 
                GROUP BY teaching_type, teaching_factory 
                ORDER BY 
                    CASE 
                        WHEN teaching_type LIKE '試點%%' THEN 1 
                        WHEN teaching_type LIKE '試跑%%' THEN 2 
                        WHEN teaching_type LIKE '正式交付%%' THEN 3 
                        ELSE 4 
                    END,         
                    CAST(SUBSTRING(teaching_type, 
                        CASE 
                            WHEN teaching_type LIKE '試點%%' THEN 3 
                            WHEN teaching_type LIKE '試跑%%' THEN 3 
                            WHEN teaching_type LIKE '正式交付%%' THEN 5 
                            ELSE 1 
                        END) AS UNSIGNED) ASC
            """
            )
        cursor.execute(sql, [course_name_value])
        rows = cursor.fetchall()
        if export_csv:
            # 一致化：落盘导出 + 目录数量达到阈值时清空
            purged, before_count = _purge_exports_if_limit()
            header = 'teaching_type,avg_score,record_count,details\n'
            csv_lines = []
            for r in rows:
                details = (r.get('details') or '').replace(',', ';')  # 防止逗号破坏列
                csv_lines.append(f"\"{r['teaching_type']}\",{r['avg_score']},{r['record_count']},\"{details}\"")
            csv_content = header + '\n'.join(csv_lines)
            ts = datetime.now().strftime('%Y%m%d%H%M%S')
            # 使用 secure_filename 以避免潜在非法字符
            # safe_base = secure_filename(str(course_name_value)) or 'course'
            filename = f"教學記錄_{course_name_value}_{ts}.csv"
            file_path = os.path.join(EXPORT_DIR, filename)
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(csv_content)
            file_url = f"/exports/{filename}"
            return jsonify({'success': True, 'message': 'CSV 已生成', 'file': {
                'name': filename,
                'url': file_url,
                'size': os.path.getsize(file_path),
                'purgedBefore': purged,
                'previousFileCount': before_count
            }})
        # formatted = []
        # for r in rows:
        #     details_arr = r.get('details').split(',') if r.get('details') else []
        #     formatted.append({**r, 'details': details_arr})
        factory_codes = {
            '觀瀾': 'GL',
            '晉城': 'JC',
            '太原': 'TY',
            '綜保區': 'ZZK',
            '濟源': 'JY',
            '加工區': 'ZZC',
            '蘭考': 'LK',
            '龍華': 'LH',
            '鶴壁': 'HB',
            '周口': 'ZK'
        }
        formatted = []
        for r in rows:
            details_arr = r.get('details').split(',') if r.get('details') else []
            teaching_type =  r.get('teaching_type')
            
            match = re.match(r'([^\d]+)(\d+)$', teaching_type)
            if match:
                prefix = match.group(1)
                number = match.group(2)
            else:
                prefix = teaching_type
                number = ""
                
            # factory_code = factory_codes[r.get('teaching_factory')]
            factory_code = factory_codes.get(r.get('teaching_factory'))
            new_teaching_type = f"{prefix}{factory_code}{number}" if number else f"{prefix}{factory_code}"    
            
            formatted.append({**r, 'details': details_arr,'new_teaching_type':new_teaching_type})

        return jsonify({'success': True, 'data': formatted, 'total': len(formatted), 'message': f"成功查询到 {len(formatted)} 个教学类型的数据"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/teaching-record/bar_coursename', methods=['GET'])
def teaching_record_bar():
    course_name_value = request.args.get('course_name_value')
    if not course_name_value:
        return jsonify({'success': False, 'message': '缺少必需参数 course_name_value'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = (
            "SELECT teaching_factory, COUNT(*) AS factory_count FROM (SELECT DISTINCT teaching_factory, teaching_type FROM teaching_record "
            "WHERE course_name = %s AND teaching_type LIKE '%%正式交付%%') AS distinct_data GROUP BY teaching_factory ORDER BY factory_count DESC"
        )
        cursor.execute(sql, [course_name_value])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': {
            'teaching_factory': [r['teaching_factory'] for r in rows],
            'factory_count': [r['factory_count'] for r in rows]
        }, 'total': len(rows), 'message': f"成功查询到 {len(rows)} 条正式交付记录"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/teaching-record/group_coursename', methods=['GET'])
def teaching_record_group():
    course_name_value = request.args.get('course_name_value')
    if not course_name_value:
        return jsonify({'success': False, 'message': '缺少必需参数 course_name_value'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        # sql = (
        #     "SELECT sub.district, sub.batch_number, sub.name, ROUND(AVG(sub.teaching_score), 2) AS avg_score, COUNT(*) AS record_count "
        #     "FROM (SELECT tr.*, td.district FROM teaching_record tr LEFT JOIN teacher_details td ON tr.name = td.name) AS sub "
        #     "WHERE sub.course_name = %s AND sub.teaching_type LIKE '%%正式交付%%' "
        #     "GROUP BY sub.district, sub.batch_number, sub.name ORDER BY sub.district ASC, sub.batch_number ASC, sub.name ASC"
        # )

        sql = (
            "SELECT * "
            "FROM ( "
            "    (    "
            "    SELECT "
            "        sub.course_name, "
            "        sub.district, "
            "        sub.batch_number, "
            "        sub.name, "
            "        ROUND(AVG(sub.teaching_score), 2) AS avg_score, "
            "        GROUP_CONCAT(sub.teaching_score ORDER BY CAST(SUBSTRING(ANY_VALUE(sub.teaching_type), 5) AS UNSIGNED)) AS score_list "
            "    FROM ( "
            "        SELECT tr.*, td.district "
            "        FROM teaching_record tr "
            "        LEFT JOIN teacher_details td ON tr.name = td.name "
            "    ) AS sub "
            "    WHERE sub.course_name = %s "
            "        AND sub.teaching_type LIKE '%%正式交付%%' "
            "    GROUP BY sub.district, sub.batch_number, sub.name "
            "    ORDER BY sub.name, CAST(SUBSTRING(ANY_VALUE(sub.teaching_type), 5) AS UNSIGNED) "
            "    ) "
            "        UNION ALL "
            "        (SELECT "
            "            course AS course_name, "
            "            area AS district, "
            "            shift AS batch_number, "
            "            applicant AS name, "
            "            score AS avg_score, "
            "            CONCAT(score, '_list') AS score_list "
            "        FROM incubation) "
            ") AS combined "
            "WHERE course_name = %s "
            "ORDER BY district ASC, batch_number ASC, name ASC;"
        )

        cursor.execute(sql, [course_name_value, course_name_value])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': rows, 'total': len(rows), 'message': f"成功查询到 {len(rows)} 个分组的数据"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/teaching-record/course-name-options', methods=['GET'])
def teaching_record_course_name_options():
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('SELECT DISTINCT course_name FROM teaching_record ORDER BY course_name ASC')
        rows = cursor.fetchall()
        options = [{'label': r['course_name'], 'value': r['course_name']} for r in rows]
        return jsonify({'Options': options})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取课程名称选项失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

# ---------------- Lecturer Analysis APIs (migrated) ----------------

@app.route('/api/lecturer-analysis/name-options', methods=['GET'])
def lecturer_name_options():
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = (
            "SELECT DISTINCT name FROM ("
            "    SELECT name FROM teacher_details "
            "    UNION "
            "    SELECT applicant AS name FROM incubation"
            ") AS combined_tables "
            "ORDER BY name ASC"
        )
        cursor.execute(sql)
        rows = cursor.fetchall()
        options = [{'label': r['name'], 'value': r['name']} for r in rows]
        return jsonify({'Options': options})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取讲师名称选项失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/lecturer-analysis/teachingdata', methods=['GET'])
def lecturer_teaching_data():
    lecturer_name = request.args.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        # sql = (
        #     "WITH RankedTeaching AS ( "
        #     "SELECT tr.*, ROW_NUMBER() OVER (PARTITION BY NAME ORDER BY teaching_type DESC) AS rn FROM teaching_record tr ) "
        #     "SELECT td.*, rt.teaching_instructor_type FROM teacher_details td "
        #     "LEFT JOIN RankedTeaching rt ON td.NAME = rt.NAME AND rt.rn = 1 WHERE td.name = %s"
        # )
        sql = (
            "SELECT td.*, rt.teaching_instructor_type FROM teacher_details td "
            "LEFT JOIN ("
            "    SELECT tr1.* FROM teaching_record tr1 "
            "    INNER JOIN ("
            "        SELECT NAME, MAX(teaching_type) as max_teaching_type "
            "        FROM teaching_record "
            "        GROUP BY NAME"
            "    ) tr2 ON tr1.NAME = tr2.NAME AND tr1.teaching_type = tr2.max_teaching_type"
            ") rt ON td.NAME = rt.NAME "
            "WHERE td.name = %s"
        )
        cursor.execute(sql, [lecturer_name])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': (rows[0] if rows else None), 'total': len(rows), 'message': f"成功查询到 {len(rows)} 个分组的数据"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询讲师信息失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

@app.route('/api/lecturer-analysis/teachingscore', methods=['GET'])
def lecturer_teaching_score():
    lecturer_name = request.args.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = (
            "SELECT name, "
            "SUM(CASE WHEN type = '試點' THEN 1 ELSE 0 END) AS pilot_count, "
            "ROUND(AVG(CASE WHEN type = '試點' THEN teaching_score ELSE NULL END), 2) AS pilot_avg, "
            "SUM(CASE WHEN type = '試跑' THEN 1 ELSE 0 END) AS trial_count, "
            "ROUND(AVG(CASE WHEN type = '試跑' THEN teaching_score ELSE NULL END), 2) AS trial_avg, "
            "SUM(CASE WHEN type = '正式交付' THEN 1 ELSE 0 END) AS formal_count, "
            "ROUND(AVG(CASE WHEN type = '正式交付' THEN teaching_score ELSE NULL END), 2) AS formal_avg "
            "FROM ( SELECT name, CASE WHEN teaching_type LIKE '%%正式交付%%' THEN '正式交付' "
            "WHEN teaching_type LIKE '%%試點%%' THEN '試點' WHEN teaching_type LIKE '%%試跑%%' THEN '試跑' ELSE '其他' END AS type, teaching_score FROM teaching_record ) AS sub "
            "WHERE sub.name = %s GROUP BY name"
        )
        cursor.execute(sql, [lecturer_name])
        rows = cursor.fetchall()
        return jsonify({'success': True, 'data': (rows[0] if rows else None), 'total': len(rows), 'message': f"成功查询到 {len(rows)} 个分组的数据"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询讲师信息失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/lecturer-analysis/teachingscore_line', methods=['GET'])
def lecturer_teachingscore_line():
    lecturer_name = request.args.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = (
            "SELECT course_name, "
            "GROUP_CONCAT(DISTINCT teaching_type ORDER BY "
            "   CASE "
            "       WHEN teaching_type LIKE '試點%%' THEN 1 "
            "       WHEN teaching_type LIKE '試跑%%' THEN 2 "
            "       WHEN teaching_type LIKE '正式交付%%' THEN 3 "
            "       ELSE 4 "
            "   END, "
            "   CAST(SUBSTRING(teaching_type, CHAR_LENGTH(SUBSTRING_INDEX(teaching_type, ' ', 1)) + 2) AS UNSIGNED)"
            ") AS teaching_types, "
            "GROUP_CONCAT(teaching_score ORDER BY "
            "   CASE "
            "       WHEN teaching_type LIKE '試點%%' THEN 1 "
            "       WHEN teaching_type LIKE '試跑%%' THEN 2 "
            "       WHEN teaching_type LIKE '正式交付%%' THEN 3 "
            "       ELSE 4 "
            "   END, "
            "   CAST(SUBSTRING(teaching_type, CHAR_LENGTH(SUBSTRING_INDEX(teaching_type, ' ', 1)) + 2) AS UNSIGNED)"
            ") AS teaching_scores, "
            "GROUP_CONCAT(teaching_factory ORDER BY "
            "   CASE "
            "       WHEN teaching_type LIKE '試點%%' THEN 1 "
            "       WHEN teaching_type LIKE '試跑%%' THEN 2 "
            "       WHEN teaching_type LIKE '正式交付%%' THEN 3 "
            "       ELSE 4 "
            "   END, "
            "   CAST(SUBSTRING(teaching_type, CHAR_LENGTH(SUBSTRING_INDEX(teaching_type, ' ', 1)) + 2) AS UNSIGNED)"
            ") AS teaching_factory "
            "FROM teaching_record "
            "WHERE name = %s "
            "GROUP BY course_name"
        )
        cursor.execute(sql, [lecturer_name])
        rows = cursor.fetchall()
        processed = []
        factory_codes = {
            '觀瀾': 'GL',
            '晉城': 'JC',
            '太原': 'TY',
            '綜保區': 'ZZK',
            '濟源': 'JY',
            '加工區': 'ZZC',
            '蘭考': 'LK',
            '龍華': 'LH',
            '鶴壁': 'HB',
            '周口': 'ZK'
        }

        # 第一步：为每个课程生成 new_teaching_types
        for course in rows:
            teaching_types = course.get('teaching_types', '').split(',')
            teaching_factories = course.get('teaching_factory', '').split(',')
            
            new_teaching_types = []
            
            for i, teaching_type in enumerate(teaching_types):
                if i < len(teaching_factories):
                    factory = teaching_factories[i]
                    
                    match = re.match(r'([^\d]+)(\d+)$', teaching_type.strip())
                    if match:
                        prefix = match.group(1)
                        number = match.group(2)
                    else:
                        prefix = teaching_type.strip()
                        number = ""
                        
                    factory_code = factory_codes.get(factory.strip(), factory.strip())
                    new_teaching_type = f"{prefix}{factory_code}{number}" if number else f"{prefix}{factory_code}"
                    new_teaching_types.append(new_teaching_type)
            
            course['new_teaching_types'] = new_teaching_types

        # 第二步：找出所有课程中相同的 teaching_type 并合并显示
        # 创建一个字典来存储每个 teaching_type 对应的工厂代码
        teaching_type_factories = {}

        # 收集所有 teaching_type 和对应的工厂代码
        for course in rows:
            teaching_types = course.get('teaching_types', '').split(',')
            teaching_factories = course.get('teaching_factory', '').split(',')
            
            for i, teaching_type in enumerate(teaching_types):
                if i < len(teaching_factories):
                    factory = teaching_factories[i].strip()
                    factory_code = factory_codes.get(factory, factory)
                    
                    if teaching_type not in teaching_type_factories:
                        teaching_type_factories[teaching_type] = set()
                    
                    teaching_type_factories[teaching_type].add(factory_code)

        # 第三步：创建合并后的 teaching_type 映射
        merged_teaching_types = {}
        for teaching_type, factories in teaching_type_factories.items():
            match = re.match(r'([^\d]+)(\d+)$', teaching_type.strip())
            if match:
                prefix = match.group(1)
                number = match.group(2)
                
                if len(factories) == 1:
                    # 只有一个工厂
                    factory_code = list(factories)[0]
                    merged_teaching_types[teaching_type] = f"{prefix}{factory_code}{number}"
                else:
                    # 多个工厂，用 & 连接
                    sorted_factories = sorted(list(factories))
                    factories_str = '&'.join(sorted_factories)
                    merged_teaching_types[teaching_type] = f"{prefix}{factories_str}{number}"
            else:
                # 没有数字的情况
                prefix = teaching_type.strip()
                if len(factories) == 1:
                    factory_code = list(factories)[0]
                    merged_teaching_types[teaching_type] = f"{prefix}{factory_code}"
                else:
                    sorted_factories = sorted(list(factories))
                    factories_str = '&'.join(sorted_factories)
                    merged_teaching_types[teaching_type] = f"{prefix}{factories_str}"

        # 第四步：更新每个课程的 new_teaching_types
        for course in rows:
            teaching_types = course.get('teaching_types', '').split(',')
            merged_types = []
            
            for teaching_type in teaching_types:
                if teaching_type in merged_teaching_types:
                    merged_types.append(merged_teaching_types[teaching_type])
                else:
                    merged_types.append(teaching_type)  #  fallback
            
            course['merged_teaching_types'] = ','.join(merged_types)
        for r in rows:
            teaching_types = (r.get('teaching_types') or '').split(',') if r.get('teaching_types') else []
            merged_teaching_types = (r.get('merged_teaching_types') or '').split(',') if r.get('merged_teaching_types') else []
            teaching_scores = [float(s) for s in ((r.get('teaching_scores') or '').split(',')) if s]
            processed.append({'course_name': r['course_name'], 'teaching_type': teaching_types, 'teaching_score': teaching_scores, 'new_teaching_type': merged_teaching_types})
        return jsonify({'success': True, 'data': processed, 'total': len(processed), 'message': f"成功查询到 {len(processed)} 个分组的数据"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询讲师信息失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

# @app.route('/api/lecturer-analysis/export', methods=['GET'])
# def lecturer_export_details():
#     lecturer_name = request.args.get('lecturer_name')
#     if not lecturer_name:
#         return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
#     export_csv = request.args.get('export_csv') == 'true'
#     conn = cursor = None
#     try:
#         conn, cursor = get_db_connection()
#         cursor.execute('SELECT * FROM teacher_details WHERE name = %s', [lecturer_name])
#         rows = cursor.fetchall()
#         if export_csv:
#             purged, before_count = _purge_exports_if_limit()
#             header_fields = ['name','employee_id','position_number','position_work','department','district','factory_area','educational_background','phone_number','email_number','introduction']
#             header = ','.join(header_fields) + '\n'
#             csv_lines = []
#             for r in rows:
#                 line_parts = []
#                 for f in header_fields:
#                     v = r.get(f, '') if r else ''
#                     if v is None: v = ''
#                     v = str(v).replace('"', '""')
#                     line_parts.append(f'"{v}"')
#                 csv_lines.append(','.join(line_parts))
#             csv_content = header + '\n'.join(csv_lines)
#             ts = datetime.now().strftime('%Y%m%d%H%M%S')
#             filename = f"讲师详情_{lecturer_name}_{ts}.csv"
#             file_path = os.path.join(EXPORT_DIR, filename)
#             with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
#                 f.write(csv_content)
#             file_url = f"/exports/{filename}"
#             return jsonify({'success': True, 'message': 'CSV 已生成', 'file': {
#                 'name': filename,
#                 'url': file_url,
#                 'size': os.path.getsize(file_path),
#                 'purgedBefore': purged,
#                 'previousFileCount': before_count
#             }})
#         return jsonify({'success': True, 'data': rows, 'total': len(rows), 'message': f"成功查询到 {len(rows)} 条讲师详情记录"})
#     except DatabaseConnectionError as e:
#         return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
#     except Exception as e:
#         return jsonify({'success': False, 'message': '查询教学记录失败', 'error': str(e)}), 500
#     finally:
#         if cursor:
#             try: cursor.close()
#             except Exception: pass
#         if conn:
#             try: conn.close()
#             except Exception: pass

@app.route('/api/lecturer-analysis/export', methods=['GET'])
def lecturer_export_details():
    lecturer_name = request.args.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    export_csv = request.args.get('export_csv') == 'true'
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        sql = (
            "SELECT "
            "    t1.name, "
            "    t1.employee_id, "
            "    t1.teaching_instructor_type, "
            "    t1.position_number, "
            "    t1.position_work, "
            "    t1.department, "
            "    t1.district, "
            "    t1.factory_area, "
            "    t1.graduation_school, "
            "    t1.educational_background, "
            "    COALESCE(t2.course_info, '/') AS course_info "
            "FROM ("
            # 子查询1：教师详情 + 最新教学类型
            "    SELECT "
            "        td.name, "
            "        td.employee_id, "
            "        td.position_number, "
            "        td.position_work, "
            "        td.department, "
            "        td.district, "
            "        td.factory_area, "
            "        td.graduation_school, "
            "        td.educational_background, "
            "        rt.teaching_instructor_type "
            "    FROM "
            "        teacher_details td "
            "    LEFT JOIN ("
            "        SELECT "
            "            tr1.name, "
            "            tr1.teaching_instructor_type "
            "        FROM "
            "            teaching_record tr1 "
            "        INNER JOIN ("
            "            SELECT "
            "                name, "
            "                MAX(teaching_type) AS max_teaching_type "
            "            FROM "
            "                teaching_record "
            "            GROUP BY "
            "                name "
            "        ) tr2 "
            "        ON tr1.name = tr2.name AND tr1.teaching_type = tr2.max_teaching_type "
            "    ) rt "
            "    ON td.name = rt.name "
            ") t1 "
            "LEFT JOIN ("
            # 子查询2：课程信息汇总
            "    SELECT "
            "        name, "
            "        GROUP_CONCAT("
            "            CONCAT("
            "                course_name, "
            "                '-', latest_batch_number, "
            "                '-', avg_teaching_score"
            "            ) "
            "            SEPARATOR ', '"
            "        ) AS course_info "
            "    FROM ("
            "        SELECT "
            "            d.course_name, "
            "            d.name, "
            "            ("
            "                SELECT batch_number "
            "                FROM teaching_record "
            "                WHERE "
            "                    course_name = d.course_name "
            "                    AND name = d.name "
            "                    AND (teaching_type LIKE '%試跑%' OR teaching_type LIKE '%正式交付%') "
            "                ORDER BY teaching_date DESC "
            "                LIMIT 1 "
            "            ) AS latest_batch_number, "
            "            ROUND(AVG(d.teaching_score), 2) AS avg_teaching_score "
            "        FROM ("
            "            SELECT DISTINCT "
            "                course_name, "
            "                teaching_type, "
            "                teaching_date, "
            "                batch_number, "
            "                name, "
            "                teaching_instructor_type, "
            "                teaching_score "
            "            FROM "
            "                teaching_record "
            "            WHERE "
            "                teaching_type LIKE '%試跑%' OR teaching_type LIKE '%正式交付%' "
            "        ) AS d "
            "        GROUP BY "
            "            d.course_name, d.name "
            "    ) AS subquery "
            "    GROUP BY "
            "        name "
            ") t2 "
            "ON t1.name = t2.name"
        )   
        cursor.execute(sql)
        rows = cursor.fetchall()
        if export_csv:
            purged, before_count = _purge_exports_if_limit()
            # 定义基础字段
            base_fields = ['name', 'employee_id', 'teaching_instructor_type', 'position_number', 
                        'position_work', 'department', 'district', 'factory_area', 'graduation_school',
                        'educational_background']

            # 初始化动态课程字段（最多支持 N 门课程）
            max_courses = 0
            csv_lines = []

            for r in rows:
                line_parts = []
                
                # 1. 处理基础字段
                for f in base_fields:
                    v = r.get(f, '') if r else ''
                    if v is None:
                        v = ''
                    v = str(v).replace('"', '""')
                    line_parts.append(f'"{v}"')
                
                # 2. 处理 course_info 字段
                course_info = r.get('course_info', '') if r else ''
                courses = []
                if course_info:
                    # 分割课程信息（可能有多门课程）
                    courses = [c.strip() for c in course_info.split(',')]
                max_courses = max(len(courses),max_courses)

                # 3. 动态填充课程信息
                for i in range(1, max_courses + 1):
                    if i <= len(courses):
                        # 解析当前课程
                        course_data = courses[i-1].split('-')
                        if len(course_data) >= 3:
                            course_name = course_data[0].strip()
                            course_hours = course_data[1].strip()
                            course_score = course_data[2].strip()
                        else:
                            course_name, course_hours, course_score = '', '', ''
                    else:
                        # 如果课程数量不足 max_courses，填充空值
                        course_name, course_hours, course_score = '', '', ''
                    
                    # 添加到当前行
                    line_parts.append(f'"{course_name}"')
                    line_parts.append(f'"{course_hours}"')
                    line_parts.append(f'"{course_score}"')
                
                # 4. 添加到 CSV 行
                csv_lines.append(','.join(line_parts))
            # 初始化动态课程字段（最多支持 N 门课程）
            course_fields = []
            for i in range(1, max_courses + 1):
                course_fields.extend([
                    f'course_name_{i}',
                    f'course_hours_{i}',
                    f'course_score_{i}'
                ])

            # 组合所有字段
            header_fields = base_fields + course_fields
            header = ','.join(header_fields) + '\n'

            # 生成 CSV 内容
            csv_content = header + '\n'.join(csv_lines)
            ts = datetime.now().strftime('%Y%m%d%H%M%S')
            # filename = f"讲师详情_{lecturer_name}_{ts}.csv"
            filename = f"讲师详情_{ts}.csv"
            file_path = os.path.join(EXPORT_DIR, filename)

            # 写入文件
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(csv_content)            
            file_url = f"/exports/{filename}"
            return jsonify({'success': True, 'message': 'CSV 已生成', 'file': {
                'name': filename,
                'url': file_url,
                'size': os.path.getsize(file_path),
                'purgedBefore': purged,
                'previousFileCount': before_count
            }})
        return jsonify({'success': True, 'data': rows, 'total': len(rows), 'message': f"成功查询到 {len(rows)} 条讲师详情记录"})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '查询教学记录失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

def _find_existing_photo(filename):
    if not filename:
        return None
    path = os.path.join(UPLOAD_BASE, os.path.basename(filename))
    return path if os.path.exists(path) else None

def _generate_unique_filename(original_name):
    base, ext = os.path.splitext(original_name)
    if ext.lower() not in ALLOWED_IMAGE_EXT:
        ext = '.jpg'
    # unique = datetime.now().strftime('%Y%m%d%H%M%S%f')
    unique = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"lecturer_{unique}{ext.lower()}"

@app.route('/api/lecturer-analysis/upload-photo', methods=['POST'])
def lecturer_upload_photo():
    lecturer_name = request.form.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    # 1. 归一化文件名，处理中文全角符号，防止扩展名丢失
    original_name = file.filename
    normalized_name = unicodedata.normalize('NFKC', original_name).replace('．', '.')
    filename = secure_filename(normalized_name)
    # 2. 拆分扩展名
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    # 3. 如果没有扩展名但 MIME 是图片，尝试从 MIME 推断
    if (not ext or ext == '.') and file.mimetype:
        guessed = mimetypes.guess_extension(file.mimetype.split(';')[0].strip()) or ''
        if guessed:
            # 统一 .jpe => .jpg
            if guessed == '.jpe':
                guessed = '.jpg'
            ext = guessed
            filename = filename.rstrip('.') + ext
    # 4. 特殊情况：部分浏览器给出 .jfif 也属于 jpeg
    if ext == '.jfif':
        ext = '.jpg'
        if not filename.endswith('.jpg'):
            filename = os.path.splitext(filename)[0] + '.jpg'
    # 5. 校验扩展或 MIME
    if ext not in ALLOWED_IMAGE_EXT and not (file.mimetype and file.mimetype.startswith('image/')):
        return jsonify({'success': False, 'message': '只能上传图片文件', 'detail': {
            'filename': original_name,
            'normalized': filename,
            'mimetype': file.mimetype,
            'ext': ext
        }}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('SELECT name, photo_upload FROM teacher_details WHERE name = %s', [lecturer_name])
        lecturer = cursor.fetchone()
        if not lecturer:
            return jsonify({'success': False, 'message': '讲师不存在'}), 404
        # 删除旧文件
        old_url = lecturer.get('photo_upload')
        old_path = _find_existing_photo(old_url)
        if old_path:
            try: os.remove(old_path)
            except Exception: pass
        new_filename = _generate_unique_filename(filename)
        save_path = os.path.join(UPLOAD_BASE, new_filename)
        file.save(save_path)
        photo_url = f"/uploads/photos/{new_filename}"
        cursor.execute('UPDATE teacher_details SET photo_upload = %s WHERE name = %s', [photo_url, lecturer_name])
        return jsonify({'success': True, 'message': '照片上传成功', 'data': {'photo_url': photo_url, 'filename': new_filename}})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        # 如果已保存文件且失败，可尝试删除
        return jsonify({'success': False, 'message': '上传照片失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/lecturer-analysis/delete-photo', methods=['POST'])
def lecturer_delete_photo():
    data = request.get_json(force=True, silent=True) or {}
    lecturer_name = data.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('SELECT name, photo_upload FROM teacher_details WHERE name = %s', [lecturer_name])
        lecturer = cursor.fetchone()
        if not lecturer:
            return jsonify({'success': False, 'message': '讲师不存在'}), 404
        current_url = lecturer.get('photo_upload')
        if not current_url:
            return jsonify({'success': False, 'message': '该讲师没有上传照片'}), 400
        photo_path = _find_existing_photo(current_url)
        if photo_path:
            try: os.remove(photo_path)
            except Exception: pass
        cursor.execute('UPDATE teacher_details SET photo_upload = NULL WHERE name = %s', [lecturer_name])
        return jsonify({'success': True, 'message': '照片删除成功'})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '删除照片失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass


@app.route('/api/lecturer-analysis/photo-url', methods=['GET'])
def lecturer_photo_url():
    lecturer_name = request.args.get('lecturer_name')
    if not lecturer_name:
        return jsonify({'success': False, 'message': '缺少必需参数 lecturer_name'}), 400
    conn = cursor = None
    try:
        conn, cursor = get_db_connection()
        cursor.execute('SELECT name, photo_upload FROM teacher_details WHERE name = %s', [lecturer_name])
        lecturer = cursor.fetchone()
        if not lecturer:
            return jsonify({'success': False, 'message': '讲师不存在'}), 404
        return jsonify({'success': True, 'data': {'photo_url': lecturer.get('photo_upload') or None}})
    except DatabaseConnectionError as e:
        return jsonify({'success': False, 'message': '数据库连接失败', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': '获取照片URL失败', 'error': str(e)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

# 静态访问上传的照片
@app.route('/uploads/photos/<path:filename>', methods=['GET'])
def serve_uploaded_photo(filename):
    # 防止路徑穿越
    safe_path = safe_join(UPLOAD_BASE, filename)
    if not safe_path or not os.path.exists(safe_path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    return send_file(safe_path)

@app.route('/exports/<path:filename>', methods=['GET'])
def serve_export_file(filename):
    # 防止路徑穿越
    path = safe_join(EXPORT_DIR, filename)
    if not path or not os.path.exists(path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    # 新逻辑：默认保留文件，只有明确传入 keep=false 时下载后删除
    keep_param = request.args.get('keep')
    delete_after = False
    if keep_param is not None and keep_param.strip().lower() == 'false':
        delete_after = True
    if delete_after:
        @after_this_request
        def _remove_file(response):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            return response
    return send_file(path, as_attachment=True, download_name=filename)

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    # 可选：启动前快速测试连接
    try:
        conn, c = get_db_connection()
        c.close(); conn.close()
        print('[启动检查] 数据库连接正常')
    except Exception as e:
        print('[启动检查] 数据库连接失败:', e)
    app.run(host='0.0.0.0', port=1717, debug=True)