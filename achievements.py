# 현재 로그인 사용자의 BookOasis 독서 업적을 계산하고 해금 상태를 저장합니다.
from __future__ import annotations

import json
import logging
import threading
from datetime import date, datetime, timedelta

from plugins.metadata.base import BaseMetadataProvider

from .definitions import ACHIEVEMENT_DEFINITIONS, CATEGORY_DEFINITIONS, DEFINITION_REVISION


PLUGIN_VERSION = "1.2.0"
logger = logging.getLogger(__name__)

_UNLOCK_TABLE = "plugin_achievement_unlocks"
_FIXED_PAGE_FORMATS = {"7z", "cbz", "cbr", "pdf", "rar", "tar", "zip"}


class AchievementsMetadataProvider(BaseMetadataProvider):
    """독서 활동을 사용자별 업적 카드와 진행률로 제공합니다."""

    id = "achievements"
    name = "독서 업적"
    version = PLUGIN_VERSION
    is_searchable = False
    config_schema = []
    dashboard_widget = None
    category_tab = {
        "title": "독서 업적",
        "icon": "fa-solid fa-trophy",
        "order": 85,
        "sessions": "all",
    }
    update_manifest = {
        "enabled": True,
        "provider": "github-raw",
        "raw_base_url": "https://raw.githubusercontent.com/colaiuta77/achievements/main",
        "files": [
            "achievements.py",
            "definitions.py",
            "__init__.py",
            "VERSION",
            "index.html",
            "style.css",
            "script.js",
        ],
        "version_file": "VERSION",
        "version_key": "plugin version",
        "show_sample_update_button": True,
    }

    def __init__(self):
        self._storage_ready = False
        self._storage_lock = threading.Lock()

    def search(self, db_type, query):
        return []

    def apply(self, db_type, book_id, item_data):
        return False, "독서 업적 플러그인은 메타데이터 적용을 지원하지 않습니다."

    @staticmethod
    def _row_dict(row):
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def _int(value, default=0):
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _display_number(value):
        normalized = float(value)
        return int(normalized) if normalized.is_integer() else round(normalized, 1)

    @staticmethod
    def _is_admin(user):
        return str(user.get("role") or "").strip().lower() == "admin"

    def _current_user(self):
        try:
            from flask import has_request_context, session

            if not has_request_context():
                return None
            user_id = self._int(session.get("user_id"))
        except (ImportError, RuntimeError):
            return None

        if user_id <= 0:
            return None

        row = self.get_db_gateway("general").fetch_one(
            """
            SELECT id, username, role, has_adult_access, has_audiobook_access
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        return self._row_dict(row)

    def _accessible_db_types(self, user):
        db_types = ["general", "video"]
        if self._is_admin(user) or self._int(user.get("has_adult_access")) == 1:
            db_types.append("adult")
        if self._is_admin(user) or self._int(user.get("has_audiobook_access"), 1) == 1:
            db_types.append("audiobook")
        return db_types

    @staticmethod
    def _permission_join(user, book_alias="b", progress_alias="p"):
        if AchievementsMetadataProvider._is_admin(user):
            return ""
        return (
            " JOIN user_category_permissions achievement_permission"
            f" ON achievement_permission.library_id = {book_alias}.library_id"
            f" AND achievement_permission.user_id = {progress_alias}.user_id"
            " AND achievement_permission.has_access = 1"
        )

    def _fetch_book_rows(self, db_type, user):
        gateway = self.get_db_gateway(db_type)
        permission_join = self._permission_join(user)
        rows = gateway.fetch_all(
            f"""
            SELECT
                p.book_id,
                p.pages_read,
                p.is_completed,
                p.last_read_at,
                b.total_pages,
                b.file_format,
                b.genre,
                b.tags
            FROM user_progress p
            JOIN books b ON b.id = p.book_id
            {permission_join}
            WHERE p.user_id = ?
              AND COALESCE(b.is_deleted, 0) = 0
            """,
            (self._int(user["id"]),),
        ) or []
        return [dict(row) for row in rows]

    def _fetch_single_book(self, db_type, user, book_id):
        gateway = self.get_db_gateway(db_type)
        if self._is_admin(user):
            permission_join = ""
            params = (self._int(book_id),)
        else:
            permission_join = (
                " JOIN user_category_permissions achievement_permission"
                " ON achievement_permission.library_id = b.library_id"
                " AND achievement_permission.user_id = ?"
                " AND achievement_permission.has_access = 1"
            )
            params = (self._int(user["id"]), self._int(book_id))
        row = gateway.fetch_one(
            f"""
            SELECT
                b.id AS book_id,
                0 AS pages_read,
                0 AS is_completed,
                NULL AS last_read_at,
                b.total_pages,
                b.file_format,
                b.genre,
                b.tags
            FROM books b
            {permission_join}
            WHERE b.id = ?
              AND COALESCE(b.is_deleted, 0) = 0
            """,
            params,
        )
        return self._row_dict(row)

    def _fetch_read_dates(self, db_type, user):
        gateway = self.get_db_gateway(db_type)
        permission_join = self._permission_join(user, book_alias="b", progress_alias="reading_log")
        rows = gateway.fetch_all(
            f"""
            SELECT DISTINCT reading_log.read_date
            FROM user_reading_log reading_log
            JOIN books b ON b.id = reading_log.book_id
            {permission_join}
            WHERE reading_log.user_id = ?
              AND reading_log.pages_read_delta > 0
              AND COALESCE(b.is_deleted, 0) = 0
            """,
            (self._int(user["id"]),),
        ) or []
        return {str(dict(row).get("read_date") or "")[:10] for row in rows}

    def _fetch_audiobook_rows(self, user):
        gateway = self.get_db_gateway("audiobook")
        permission_join = self._permission_join(user, book_alias="a", progress_alias="p")
        rows = gateway.fetch_all(
            f"""
            SELECT
                p.audiobook_id,
                p.current_time,
                p.total_progress_pct,
                p.is_completed,
                p.last_listened_at,
                a.total_duration
            FROM audiobook_progress p
            JOIN audiobooks a ON a.id = p.audiobook_id
            {permission_join}
            WHERE p.user_id = ?
              AND COALESCE(a.is_deleted, 0) = 0
            """,
            (self._int(user["id"]),),
        ) or []
        return [dict(row) for row in rows]

    def _fetch_video_rows(self, user):
        gateway = self.get_db_gateway("video")
        permission_join = self._permission_join(user, book_alias="v", progress_alias="p")
        rows = gateway.fetch_all(
            f"""
            SELECT
                p.video_id,
                p.current_episode_id,
                p.total_progress_pct,
                p.is_completed,
                p.last_watched_at
            FROM video_progress p
            JOIN videos v ON v.id = p.video_id
            {permission_join}
            WHERE p.user_id = ?
              AND COALESCE(v.is_deleted, 0) = 0
            """,
            (self._int(user["id"]),),
        ) or []
        return [dict(row) for row in rows]

    @staticmethod
    def _get_pending_progress(db_types, user_id):
        try:
            from utils.redis_helper import get_redis_client, make_key

            client = get_redis_client()
            if not client:
                return {}

            allowed_types = set(db_types) & {"general", "adult"}
            pending_items = client.smembers(make_key("sync:progress:pending")) or ()
            pending = {}
            for raw_item in pending_items:
                item = raw_item.decode("utf-8") if isinstance(raw_item, bytes) else str(raw_item)
                parts = item.split(":", 2)
                if len(parts) != 3 or parts[0] not in allowed_types:
                    continue
                try:
                    item_user_id = int(parts[1])
                    book_id = int(parts[2])
                except (TypeError, ValueError):
                    continue
                if item_user_id != int(user_id):
                    continue

                try:
                    raw_payload = client.get(make_key(f"user:progress:{parts[0]}:{item_user_id}:{book_id}"))
                    if isinstance(raw_payload, bytes):
                        raw_payload = raw_payload.decode("utf-8")
                    payload = json.loads(raw_payload) if raw_payload else None
                except Exception:
                    continue
                if isinstance(payload, dict):
                    pending[(parts[0], book_id)] = payload
            return pending
        except Exception:
            return {}

    def _merge_pending_rows(self, db_type, user, rows, pending):
        merged = {self._int(row.get("book_id")): dict(row) for row in rows}
        pending_dates = set()
        for (pending_db_type, book_id), payload in pending.items():
            if pending_db_type != db_type:
                continue
            row = merged.get(book_id)
            if row is None:
                row = self._fetch_single_book(db_type, user, book_id)
                if row is None:
                    continue
                merged[book_id] = row

            persisted_pages = max(0, self._int(row.get("pages_read")))
            pending_pages = max(0, self._int(payload.get("pages_read"), persisted_pages))
            row["pages_read"] = max(persisted_pages, pending_pages)
            row["is_completed"] = max(
                self._int(row.get("is_completed")),
                self._int(payload.get("is_completed")),
            )
            if payload.get("last_read_at"):
                row["last_read_at"] = payload["last_read_at"]
            if pending_pages > persisted_pages and payload.get("last_read_at"):
                pending_dates.add(str(payload["last_read_at"])[:10])
        return list(merged.values()), pending_dates

    @staticmethod
    def _metadata_tokens(value):
        tokens = set()
        for raw_token in str(value or "").split(","):
            token = raw_token.strip().casefold()
            if token:
                tokens.add(token)
        return tokens

    def _is_book_completed(self, row):
        if self._int(row.get("is_completed")) == 1:
            return True
        total_pages = max(0, self._int(row.get("total_pages")))
        return total_pages > 0 and self._int(row.get("pages_read")) >= total_pages

    @staticmethod
    def _calculate_streaks(read_dates):
        normalized_dates = []
        for raw_value in read_dates:
            try:
                normalized_dates.append(date.fromisoformat(str(raw_value)[:10]))
            except (TypeError, ValueError):
                continue
        normalized_dates = sorted(set(normalized_dates))
        if not normalized_dates:
            return 0, 0

        longest = 1
        running = 1
        for previous, current in zip(normalized_dates, normalized_dates[1:]):
            if current == previous + timedelta(days=1):
                running += 1
                longest = max(longest, running)
            else:
                running = 1

        latest = normalized_dates[-1]
        if latest not in {date.today(), date.today() - timedelta(days=1)}:
            return 0, longest

        current_streak = 1
        cursor = latest
        known_dates = set(normalized_dates)
        while cursor - timedelta(days=1) in known_dates:
            current_streak += 1
            cursor -= timedelta(days=1)
        return current_streak, longest

    def _collect_metrics(self, user):
        accessible_types = self._accessible_db_types(user)
        pending = self._get_pending_progress(accessible_types, self._int(user["id"]))
        all_book_rows = []
        read_dates = set()

        for db_type in (value for value in accessible_types if value in {"general", "adult"}):
            rows = self._fetch_book_rows(db_type, user)
            rows, pending_dates = self._merge_pending_rows(db_type, user, rows, pending)
            all_book_rows.extend(rows)
            read_dates.update(self._fetch_read_dates(db_type, user))
            read_dates.update(pending_dates)

        completed_rows = [row for row in all_book_rows if self._is_book_completed(row)]
        started_rows = [
            row for row in all_book_rows
            if self._int(row.get("pages_read")) > 0 or self._is_book_completed(row)
        ]
        fixed_pages_read = 0
        for row in started_rows:
            file_format = str(row.get("file_format") or "").strip().lower()
            total_pages = max(0, self._int(row.get("total_pages")))
            if file_format in _FIXED_PAGE_FORMATS and total_pages > 0:
                fixed_pages_read += min(max(0, self._int(row.get("pages_read"))), total_pages)

        genres = set()
        tags = set()
        for row in completed_rows:
            genres.update(self._metadata_tokens(row.get("genre")))
            tags.update(self._metadata_tokens(row.get("tags")))

        audiobook_rows = self._fetch_audiobook_rows(user) if "audiobook" in accessible_types else []
        audiobook_started = [
            row for row in audiobook_rows
            if self._float(row.get("current_time")) > 0
            or self._float(row.get("total_progress_pct")) > 0
            or self._int(row.get("is_completed")) == 1
        ]
        audiobook_completed = [
            row for row in audiobook_rows if self._int(row.get("is_completed")) == 1
        ]
        video_rows = self._fetch_video_rows(user)
        video_started = [
            row for row in video_rows
            if row.get("current_episode_id") is not None
            or self._float(row.get("total_progress_pct")) > 0
            or self._int(row.get("is_completed")) == 1
            or bool(row.get("last_watched_at"))
        ]
        video_completed = [
            row for row in video_rows if self._int(row.get("is_completed")) == 1
        ]
        current_streak, longest_streak = self._calculate_streaks(read_dates)

        return {
            "books_started": len(started_rows),
            "books_completed": len(completed_rows),
            "fixed_pages_read": fixed_pages_read,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "reading_days": len(read_dates),
            "distinct_genres": len(genres),
            "distinct_tags": len(tags),
            "audiobooks_started": len(audiobook_started),
            "audiobooks_completed": len(audiobook_completed),
            "videos_started": len(video_started),
            "videos_completed": len(video_completed),
        }

    def _ensure_storage(self):
        if self._storage_ready:
            return
        with self._storage_lock:
            if self._storage_ready:
                return
            self.get_db_gateway("general").execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_UNLOCK_TABLE} (
                    user_id BIGINT NOT NULL,
                    achievement_key VARCHAR(96) NOT NULL,
                    unlocked_at VARCHAR(32) NOT NULL,
                    definition_version BIGINT NOT NULL,
                    evidence_value DOUBLE NOT NULL DEFAULT 0,
                    unlock_source VARCHAR(24) NOT NULL DEFAULT 'calculated',
                    PRIMARY KEY (user_id, achievement_key)
                )
                """
            )
            self._storage_ready = True

    def _load_unlocks(self, user_id):
        rows = self.get_db_gateway("general").fetch_all(
            f"""
            SELECT achievement_key, unlocked_at, definition_version, evidence_value, unlock_source
            FROM {_UNLOCK_TABLE}
            WHERE user_id = ?
            ORDER BY unlocked_at DESC, achievement_key ASC
            """,
            (user_id,),
        ) or []
        return {str(dict(row)["achievement_key"]): dict(row) for row in rows}

    def _unlock_earned(self, user_id, metrics):
        self._ensure_storage()
        gateway = self.get_db_gateway("general")
        unlocks = self._load_unlocks(user_id)
        unlocked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for definition in ACHIEVEMENT_DEFINITIONS:
            key = definition["key"]
            value = self._float(metrics.get(definition["metric"]))
            if key in unlocks or value < self._float(definition["target"]):
                continue
            try:
                gateway.execute(
                    f"""
                    INSERT INTO {_UNLOCK_TABLE} (
                        user_id, achievement_key, unlocked_at, definition_version,
                        evidence_value, unlock_source
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, key, unlocked_at, DEFINITION_REVISION, value, "calculated"),
                )
            except Exception:
                duplicate = gateway.fetch_one(
                    f"""
                    SELECT achievement_key
                    FROM {_UNLOCK_TABLE}
                    WHERE user_id = ? AND achievement_key = ?
                    """,
                    (user_id, key),
                )
                if duplicate is None:
                    raise
        return self._load_unlocks(user_id)

    @staticmethod
    def _achievement_payload(definition, metrics, unlocks):
        current = max(0.0, AchievementsMetadataProvider._float(metrics.get(definition["metric"])))
        target = max(1.0, AchievementsMetadataProvider._float(definition["target"], 1))
        unlock = unlocks.get(definition["key"])
        unlocked = unlock is not None
        progress_percent = 100 if unlocked else min(99, round((current / target) * 100))
        if unlocked:
            status = "unlocked"
        elif current > 0:
            status = "in_progress"
        else:
            status = "locked"
        return {
            **definition,
            "current": AchievementsMetadataProvider._display_number(current),
            "target": AchievementsMetadataProvider._display_number(target),
            "remaining": max(0, int(target - current)),
            "progress_percent": progress_percent,
            "status": status,
            "unlocked": unlocked,
            "unlocked_at": str(unlock.get("unlocked_at") or "") if unlock else "",
        }

    @staticmethod
    def _category_payload(achievements):
        categories = []
        for definition in CATEGORY_DEFINITIONS:
            items = [item for item in achievements if item["category"] == definition["key"]]
            unlocked = sum(1 for item in items if item["unlocked"])
            categories.append(
                {
                    **definition,
                    "total": len(items),
                    "unlocked": unlocked,
                    "progress_percent": round((unlocked / len(items)) * 100) if items else 0,
                }
            )
        return categories

    def get_dashboard_data(self, db_type, limit=100):
        try:
            user = self._current_user()
            if user is None:
                return {"success": False, "error": "로그인 후 독서 업적을 확인할 수 있습니다."}

            metrics = self._collect_metrics(user)
            unlocks = self._unlock_earned(self._int(user["id"]), metrics)
            achievements = [
                self._achievement_payload(definition, metrics, unlocks)
                for definition in ACHIEVEMENT_DEFINITIONS
            ]
            unlocked_count = sum(1 for item in achievements if item["status"] == "unlocked")
            in_progress_count = sum(1 for item in achievements if item["status"] == "in_progress")
            total_count = len(achievements)
            next_achievement = next(
                (
                    item for item in sorted(
                        (entry for entry in achievements if not entry["unlocked"]),
                        key=lambda entry: (-entry["progress_percent"], entry["remaining"], entry["target"]),
                    )
                ),
                None,
            )

            return {
                "success": True,
                "user": {"username": str(user.get("username") or "")},
                "summary": {
                    "total": total_count,
                    "unlocked": unlocked_count,
                    "in_progress": in_progress_count,
                    "locked": total_count - unlocked_count - in_progress_count,
                    "progress_percent": round((unlocked_count / total_count) * 100) if total_count else 0,
                },
                "metrics": metrics,
                "categories": self._category_payload(achievements),
                "achievements": achievements,
                "next_achievement": next_achievement,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception:
            logger.exception("독서 업적을 계산하지 못했습니다.")
            return {"success": False, "error": "독서 업적을 계산하지 못했습니다. BookOasis 로그를 확인해 주세요."}
