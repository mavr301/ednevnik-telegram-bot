import hashlib
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

BASE_URL = "https://ocjene.skole.hr"
LOGIN_URL = f"{BASE_URL}/login"
GRADES_URL = f"{BASE_URL}/grade/all"

# Mimic a Croatian browser session to avoid bot detection and get Croatian locale
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "hr,hr-HR;q=0.9,en;q=0.1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


@dataclass
class Grade:
    subject: str
    teacher: str
    date: str
    grade: Optional[int]   # None = teacher note without a numeric grade
    comment: str

    @property
    def is_note(self) -> bool:
        return self.grade is None

    def uid(self) -> str:
        key = f"{self.subject}:{self.date}:{self.grade}:{self.comment}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


class ScraperError(Exception):
    pass


class LoginError(ScraperError):
    pass


class EDnevnikScraper:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)
        self._logged_in = False

    def _get_csrf_token(self) -> str:
        resp = self.session.get(LOGIN_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token_el = soup.select_one('form > input[name="csrf_token"]')
        if not token_el:
            raise LoginError("CSRF token not found on login page")
        return token_el.get("value", "")

    def login(self) -> None:
        csrf = self._get_csrf_token()
        resp = self.session.post(
            LOGIN_URL,
            data={
                "username": self.username,
                "password": self.password,
                "csrf_token": csrf,
            },
            timeout=30,
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        error_el = soup.select_one(
            "#page-wrapper > div.flash-messages > div.alert > p"
        )
        if error_el:
            raise LoginError(f"Login failed: {error_el.get_text(strip=True)}")
        self._logged_in = True
        logger.info("Login successful")

    def get_grades(self, save_debug_html: bool = False) -> List[Grade]:
        if not self._logged_in:
            self.login()

        resp = self.session.get(GRADES_URL, timeout=30)
        resp.raise_for_status()

        if save_debug_html or os.getenv("SAVE_DEBUG_HTML"):
            path = os.path.join(os.path.dirname(os.getenv("STORAGE_FILE", "data/grades.json")), "debug_grades.html")
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            logger.info("Raw HTML saved to %s", path)

        return _parse_grades(resp.text)


def _parse_grades(html: str) -> List[Grade]:
    soup = BeautifulSoup(html, "html.parser")
    grades: List[Grade] = []

    tables = soup.select("div.flex-table.new-grades-table")
    if not tables:
        logger.warning(
            "No grade tables found. The page structure may have changed "
            "or you may not be logged in. Set SAVE_DEBUG_HTML=1 to inspect the page."
        )
        return grades

    for table in tables:
        subject, teacher = _extract_subject_info(table)
        headers = [
            h.get_text(strip=True).lower()
            for h in table.select("div.row.header div.cell > span")
        ]

        date_idx = _find_col(headers, ["datum", "date"], default=0)
        grade_idx = _find_col(headers, ["ocjena", "grade", "ocena"], default=len(headers) - 1)
        comment_idx = _find_col(headers, ["bilješka", "biljeska", "napomena", "note", "comment"], default=1)

        for row in table.select("div.row:not(.header)"):
            cells = [c.get_text(strip=True) for c in row.select("div.cell")]
            if len(cells) < 2:
                continue
            try:
                date = cells[date_idx] if date_idx < len(cells) else ""
                grade_str = cells[grade_idx] if grade_idx < len(cells) else ""
                comment = cells[comment_idx] if comment_idx < len(cells) else ""
                grade_val = int(grade_str) if grade_str.isdigit() else None
                if grade_val is None and not comment:
                    continue  # skip truly empty rows
                grades.append(
                    Grade(
                        subject=subject,
                        teacher=teacher,
                        date=date,
                        grade=grade_val,
                        comment=" ".join(comment.split()),
                    )
                )
            except (ValueError, IndexError) as e:
                logger.debug("Skipped row %s: %s", cells, e)

    logger.info("Parsed %d grades across %d tables", len(grades), len(tables))
    return grades


def _find_col(headers: List[str], keywords: List[str], default: int = 0) -> int:
    for i, h in enumerate(headers):
        if any(kw in h for kw in keywords):
            return i
    return default


def _extract_subject_info(table: Tag) -> Tuple[str, str]:
    # Subject name is stored directly in data-action-id (e.g. "Literacy", "P.E")
    # Teacher names are not present on the /grade/all page
    subject = table.get("data-action-id", "").strip()
    return subject or "Unknown Subject", ""
