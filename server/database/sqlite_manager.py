import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class SqliteManager:
    def __init__(self, db_path: str = "server/data/codebase_intelligence.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Repositories Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                github_url TEXT NOT NULL,
                branch TEXT,
                commit_hash TEXT,
                directory_map TEXT,
                status TEXT,
                architecture_analysis TEXT,
                quality_analysis TEXT,
                final_summary TEXT,
                final_report TEXT,
                created_at TEXT
            )
            """)
            
            # Files Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                repository_id TEXT,
                file_path TEXT,
                file_type TEXT,
                file_size INTEGER,
                ast_data TEXT,
                analysis TEXT,
                PRIMARY KEY (repository_id, file_path),
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            )
            """)
            
            # Dependencies Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependencies (
                repository_id TEXT,
                source_file TEXT,
                target_file TEXT,
                dependency_type TEXT,
                PRIMARY KEY (repository_id, source_file, target_file, dependency_type),
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            )
            """)
            
            # Issues Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id TEXT PRIMARY KEY,
                repository_id TEXT,
                file_path TEXT,
                line INTEGER,
                severity TEXT,
                category TEXT,
                problem TEXT,
                impact TEXT,
                recommendation TEXT,
                confidence REAL,
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            )
            """)
            conn.commit()

    def insert_repository(self, repo_id: str, github_url: str, branch: str = "main", commit_hash: str = "") -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO repositories (id, github_url, branch, commit_hash, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    github_url=excluded.github_url,
                    branch=excluded.branch,
                    commit_hash=excluded.commit_hash,
                    status=excluded.status
                """, (repo_id, github_url, branch, commit_hash, "cloning", datetime.utcnow().isoformat()))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error insert_repository: {e}")
            return False

    def update_repository_status(self, repo_id: str, status: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE repositories SET status = ? WHERE id = ?", (status, repo_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error update_repository_status: {e}")
            return False

    def update_repository_analysis(self, repo_id: str, directory_map: Dict[str, Any], 
                                   architecture_analysis: str, quality_analysis: Dict[str, Any], 
                                   final_summary: str, final_report: Dict[str, Any]) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                UPDATE repositories 
                SET directory_map = ?, architecture_analysis = ?, quality_analysis = ?, final_summary = ?, final_report = ?, status = ?
                WHERE id = ?
                """, (
                    json.dumps(directory_map),
                    architecture_analysis,
                    json.dumps(quality_analysis),
                    final_summary,
                    json.dumps(final_report),
                    "completed",
                    repo_id
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error update_repository_analysis: {e}")
            return False

    def insert_file(self, repo_id: str, file_path: str, file_type: str, file_size: int, 
                    ast_data: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO files (repository_id, file_path, file_type, file_size, ast_data, analysis)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (repo_id, file_path, file_type, file_size, json.dumps(ast_data), json.dumps(analysis)))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error insert_file: {e}")
            return False

    def insert_dependency(self, repo_id: str, source_file: str, target_file: str, dependency_type: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR IGNORE INTO dependencies (repository_id, source_file, target_file, dependency_type)
                VALUES (?, ?, ?, ?)
                """, (repo_id, source_file, target_file, dependency_type))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error insert_dependency: {e}")
            return False

    def insert_issue(self, issue_id: str, repo_id: str, file_path: str, line: int, severity: str, 
                     category: str, problem: str, impact: str, recommendation: str, confidence: float) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO issues (id, repository_id, file_path, line, severity, category, problem, impact, recommendation, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (issue_id, repo_id, file_path, line, severity, category, problem, impact, recommendation, confidence))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error insert_issue: {e}")
            return False

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["directory_map"] = json.loads(res["directory_map"]) if res["directory_map"] else None
                res["quality_analysis"] = json.loads(res["quality_analysis"]) if res["quality_analysis"] else None
                res["final_report"] = json.loads(res["final_report"]) if res["final_report"] else None
                return res
            return None

    def list_repositories(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, github_url, branch, commit_hash, status, created_at FROM repositories ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete_repository(self, repo_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"DB Error delete_repository: {e}")
            return False

    def get_files(self, repo_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path, file_type, file_size, ast_data, analysis FROM files WHERE repository_id = ?", (repo_id,))
            rows = cursor.fetchall()
            res = []
            for r in rows:
                rd = dict(r)
                rd["ast_data"] = json.loads(rd["ast_data"]) if rd["ast_data"] else None
                rd["analysis"] = json.loads(rd["analysis"]) if rd["analysis"] else None
                res.append(rd)
            return res

    def get_file(self, repo_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE repository_id = ? AND file_path = ?", (repo_id, file_path))
            row = cursor.fetchone()
            if row:
                rd = dict(row)
                rd["ast_data"] = json.loads(rd["ast_data"]) if rd["ast_data"] else None
                rd["analysis"] = json.loads(rd["analysis"]) if rd["analysis"] else None
                return rd
            return None

    def get_dependencies(self, repo_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_file, target_file, dependency_type FROM dependencies WHERE repository_id = ?", (repo_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_issues(self, repo_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_path, line, severity, category, problem, impact, recommendation, confidence FROM issues WHERE repository_id = ?", (repo_id,))
            return [dict(row) for row in cursor.fetchall()]
