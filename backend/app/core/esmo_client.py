from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import urllib3

# Suppress HTTPS warnings for local IP certificates.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("esmo")


class EsmoClient:
    """
    Client for ESMO (Elektron Tibbiy Ko'rik Tizimi).
    Uses authenticated HTML scraping because there is no public JSON API.
    """

    BROWSER_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        base_url: str = "https://192.168.8.10/cab/",
        username: str = "admin",
        password: str = "QW1665gety",
        timeout: int = 20,
        login_retries: int = 2,
        employee_max_pages: int | None = 100,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.username = username
        self.password = password
        self.timeout = max(timeout, 5)
        self.login_retries = max(login_retries, 1)
        if employee_max_pages is None or employee_max_pages <= 0:
            self.employee_max_pages = None
        else:
            self.employee_max_pages = max(employee_max_pages, 1)
        self.last_error: str | None = None
        self.is_logged_in = False
        self._exam_detail_cache: dict[int, dict[str, Any]] = {}

        parsed = urlparse(self.base_url)
        self.origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""

        self.session = requests.Session()
        self.session.verify = False
        # IMPORTANT: prevent local-device requests from being routed to global proxy.
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": self.BROWSER_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def _auth_headers(self) -> dict[str, str]:
        referer = f"{self.base_url}personal/"
        headers: dict[str, str] = {"Referer": referer}
        if self.origin:
            headers["Origin"] = self.origin
        return headers

    def _get(self, url: str) -> requests.Response:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def _looks_authenticated(self, html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")
        if soup.select_one("input[name='user_login'], input[name='user_pass']"):
            return False
        if soup.find(attrs={"data-testid": "logoutButton"}):
            return True
        if soup.find("tr", class_="item"):
            return True
        return False

    def _session_is_authenticated(self) -> bool:
        try:
            resp = self._get(f"{self.base_url}personal/")
            return self._looks_authenticated(resp.text)
        except Exception as exc:
            self.last_error = f"ESMO session check failed: {exc}"
            logger.error(self.last_error)
            return False

    def _login_once(self) -> bool:
        # Warm up session cookie first.
        try:
            self._get(f"{self.base_url}personal/")
        except Exception as exc:
            self.last_error = f"ESMO pre-login page failed: {exc}"
            logger.error(self.last_error)
            return False

        ajax_payload = {
            "user_login": self.username,
            "user_pass": self.password,
            "remember": "1",
            "cmd": "account/account_login",
        }
        login_url = f"{self.base_url}ajax.php?cmd=account/account_login"

        try:
            logger.info("Attempting ESMO AJAX login at %s", login_url)
            resp = self.session.post(login_url, data=ajax_payload, headers=self._auth_headers(), timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            self.last_error = f"ESMO AJAX login request failed: {exc}"
            logger.error(self.last_error)
            return False

        if self._session_is_authenticated():
            self.is_logged_in = True
            logger.info("ESMO login successful (AJAX)")
            return True

        # Fallback: submit login form directly.
        try:
            form_payload = {
                "user_login": self.username,
                "user_pass": self.password,
                "cmd": "account/account_login",
            }
            form_resp = self.session.post(
                f"{self.base_url}personal/",
                data=form_payload,
                headers=self._auth_headers(),
                timeout=self.timeout,
            )
            form_resp.raise_for_status()
        except Exception as exc:
            self.last_error = f"ESMO form login request failed: {exc}"
            logger.error(self.last_error)
            return False

        if self._session_is_authenticated():
            self.is_logged_in = True
            logger.info("ESMO login successful (form fallback)")
            return True

        self.last_error = "ESMO login failed (invalid credentials or changed auth flow)"
        logger.error(self.last_error)
        return False

    def login(self) -> bool:
        """
        Authenticate with ESMO.

        ESMO expects browser-like headers and local session context; otherwise the
        endpoint can return HTTP 200 XML but keep user unauthenticated.
        """
        self.last_error = None
        self.is_logged_in = False

        for attempt in range(1, self.login_retries + 1):
            if self._login_once():
                return True
            if attempt < self.login_retries:
                logger.warning("ESMO login retry %d/%d", attempt, self.login_retries)

        return False

    def fetch_latest_exams(self) -> List[Dict[str, Any]]:
        """
        Scrape current exam page.
        Kept for compatibility with existing callers.
        """
        return self.fetch_exams_since(since_esmo_id=None, max_pages=1)

    def fetch_exams_since(
        self,
        since_esmo_id: int | None,
        max_pages: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape ESMO journal with pagination and return only new exams.

        Args:
            since_esmo_id: stop when journal reaches this id or older.
            max_pages: hard cap to prevent unbounded crawl.
        """
        if not self.is_logged_in and not self.login():
            return []

        exams: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        stop_at_known = since_esmo_id is not None

        first_page_soup: BeautifulSoup | None = None
        first_page_rows: list[dict[str, Any]] = []
        first_page_url: str | None = None

        journal_candidates = [
            f"{self.base_url}pp/journal/",
            f"{self.base_url}pp/journal/page_1.html",
        ]
        for url in journal_candidates:
            try:
                resp = self._get(url)
                soup = BeautifulSoup(resp.text, "lxml")
                rows = self._parse_exam_rows(soup)
                if rows:
                    first_page_soup = soup
                    first_page_rows = rows
                    first_page_url = url
                    break
            except Exception as exc:
                logger.warning("ESMO journal page fetch failed for %s: %s", url, exc)

        if first_page_soup is not None:
            total_pages = self._extract_total_pages(first_page_soup)
            if max_pages is not None and max_pages > 0:
                pages_to_fetch = min(total_pages, max_pages)
            else:
                pages_to_fetch = total_pages
            pages_to_fetch = max(pages_to_fetch, 1)

            for page_no in range(1, pages_to_fetch + 1):
                if page_no == 1:
                    page_rows = first_page_rows
                else:
                    page_url = f"{self.base_url}pp/journal/page_{page_no}.html"
                    try:
                        resp = self._get(page_url)
                        page_soup = BeautifulSoup(resp.text, "lxml")
                        page_rows = self._parse_exam_rows(page_soup)
                    except Exception as exc:
                        logger.warning("ESMO journal page fetch failed for %s: %s", page_url, exc)
                        continue

                if not page_rows:
                    continue

                reached_known = False
                for exam in page_rows:
                    exam_id = exam.get("esmo_id")
                    if not isinstance(exam_id, int):
                        continue
                    if exam_id in seen_ids:
                        continue
                    if stop_at_known and exam_id <= since_esmo_id:
                        reached_known = True
                        break
                    seen_ids.add(exam_id)
                    exams.append(exam)

                if reached_known:
                    break

            # Enrich latest rows from monitor page where result/admittance is explicit.
            monitor_rows: list[dict[str, Any]] = []
            for monitor_url in (f"{self.base_url}monitor/",):
                try:
                    monitor_resp = self._get(monitor_url)
                    monitor_soup = BeautifulSoup(monitor_resp.text, "lxml")
                    monitor_rows = self._parse_exam_rows(monitor_soup)
                    if monitor_rows:
                        break
                except Exception as exc:
                    logger.debug("ESMO monitor enrichment failed for %s: %s", monitor_url, exc)

            if monitor_rows:
                merged_by_id: dict[int, dict[str, Any]] = {
                    int(item["esmo_id"]): item
                    for item in exams
                    if isinstance(item.get("esmo_id"), int)
                }
                for m in monitor_rows:
                    mid = m.get("esmo_id")
                    if not isinstance(mid, int):
                        continue
                    if stop_at_known and mid <= since_esmo_id and mid not in merged_by_id:
                        continue
                    current = merged_by_id.get(mid)
                    if current is None:
                        merged_by_id[mid] = m
                    else:
                        merged_by_id[mid] = {
                            **current,
                            # monitor row has authoritative current status/comment-driven result
                            **m,
                        }

                exams = sorted(merged_by_id.values(), key=lambda x: int(x.get("esmo_id") or 0), reverse=True)

            if exams:
                self.last_error = None
                return exams

            # Known checkpoint reached with no new rows is not an error.
            if stop_at_known:
                self.last_error = None
                return []

            logger.warning("ESMO journal parsed but returned no exams: %s", first_page_url)

        # Fallback for older/alternate ESMO builds.
        fallback_candidates = [
            f"{self.base_url}monitor/",
            f"{self.base_url}monitor/index.php",
            f"{self.base_url}monitor/monitor_ws.php",
        ]
        for url in fallback_candidates:
            try:
                resp = self._get(url)
                soup = BeautifulSoup(resp.text, "lxml")
                rows = self._parse_exam_rows(soup)
                if not rows:
                    continue
                for exam in rows:
                    exam_id = exam.get("esmo_id")
                    if not isinstance(exam_id, int):
                        continue
                    if exam_id in seen_ids:
                        continue
                    if stop_at_known and exam_id <= since_esmo_id:
                        continue
                    seen_ids.add(exam_id)
                    exams.append(exam)
                if exams:
                    self.last_error = None
                    return exams
            except Exception as exc:
                logger.warning("ESMO exam fetch failed for %s: %s", url, exc)
                continue

        self.last_error = "ESMO exams not found in monitor/journal pages"
        logger.error(self.last_error)
        return []

    def fetch_employees(self) -> List[Dict[str, Any]]:
        """
        Scrape personnel list from /cab/personal/.
        """
        if not self.is_logged_in and not self.login():
            return []

        personal_url = f"{self.base_url}personal/"
        try:
            resp = self._get(personal_url)
            soup = BeautifulSoup(resp.text, "lxml")

            if not self._looks_authenticated(resp.text):
                self.last_error = "ESMO session is not authenticated while reading employees"
                logger.error(self.last_error)
                return []

            employees: list[dict[str, Any]] = []
            seen: set[tuple[str, str]] = set()
            self._parse_employee_rows(soup, employees, seen)

            total_pages = self._extract_total_pages(soup)
            pages_to_fetch = total_pages if self.employee_max_pages is None else min(total_pages, self.employee_max_pages)

            for page_no in range(2, pages_to_fetch + 1):
                page_url = f"{self.base_url}personal/page_{page_no}.html"
                try:
                    page_resp = self._get(page_url)
                    page_soup = BeautifulSoup(page_resp.text, "lxml")
                    self._parse_employee_rows(page_soup, employees, seen)
                except Exception as page_exc:
                    logger.warning("ESMO employees page fetch failed (%s): %s", page_url, page_exc)
                    continue

            if self.employee_max_pages is not None and total_pages > pages_to_fetch:
                logger.warning(
                    "ESMO employees truncated: fetched %d/%d pages (employee_max_pages=%d)",
                    pages_to_fetch,
                    total_pages,
                    self.employee_max_pages,
                )

            self.last_error = None
            return employees
        except Exception as exc:
            self.last_error = f"Failed to fetch ESMO employees: {exc}"
            logger.error(self.last_error)
            return []

    def _extract_total_pages(self, soup: BeautifulSoup) -> int:
        page_nums: list[int] = []
        for a in soup.select("div.list_pages a[href]"):
            href = a.get("href", "")
            m = re.search(r"/page_(\d+)\.html", href)
            if m:
                page_nums.append(int(m.group(1)))

        links_max = max(page_nums) if page_nums else 1

        panel = soup.select_one("div.panel_diapazon_page")
        if panel:
            # Typical format: "1 ... 50 РёР· 2710" (start, end, total rows).
            nums = re.findall(r"\d+", panel.get_text(" ", strip=True))
            if len(nums) >= 3:
                try:
                    start = int(nums[0])
                    end = int(nums[1])
                    total_rows = int(nums[2])
                    per_page = end - start + 1
                    if start >= 1 and end >= start and total_rows >= end and per_page > 0:
                        by_panel = (total_rows + per_page - 1) // per_page
                        return max(by_panel, links_max, 1)
                except ValueError:
                    pass

        return max(links_max, 1)

    def _parse_employee_rows(
        self,
        soup: BeautifulSoup,
        employees: list[dict[str, Any]],
        seen: set[tuple[str, str]],
    ) -> None:
        rows = soup.find_all("tr", class_="item")
        for row in rows:
            pass_id_cell = row.select_one("td.id.propusk")
            pass_id = pass_id_cell.get_text(strip=True) if pass_id_cell else ""

            name_link = row.select_one("td.person_name a")
            full_name = name_link.get_text(strip=True) if name_link else ""

            # Fallback pass id extraction if class selector changes.
            if not pass_id:
                nums = re.findall(r"\b\d{3,10}\b", row.get_text(" ", strip=True))
                pass_id = nums[0] if nums else ""

            org = row.find("td", {"data-testid": "org"})
            department = row.find("td", {"data-testid": "otdel"})
            position = row.find("td", {"data-testid": "working"})

            key = (pass_id, full_name)
            if key in seen:
                continue
            seen.add(key)

            employees.append(
                {
                    "pass_id": pass_id,
                    "full_name": full_name,
                    "organization": org.get_text(strip=True) if org else "",
                    "department": department.get_text(strip=True) if department else "",
                    "position": position.get_text(strip=True) if position else "",
                }
            )

    def _parse_exam_rows(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        rows = soup.find_all("tr", class_="item")
        exams: list[dict[str, Any]] = []
        for row in rows:
            parsed = self._parse_exam_row(row)
            if parsed:
                exams.append(parsed)
        return exams

    def _parse_exam_row(self, row) -> Dict[str, Any] | None:
        cells = row.find_all("td", recursive=False)
        if len(cells) < 5:
            return None
        esmo_id: Optional[int] = None
        row_id = row.get("id", "")
        row_id_match = re.search(r"(\d+)$", row_id)
        if row_id_match:
            esmo_id = int(row_id_match.group(1))
        else:
            # In some ESMO views the MO id is in column 2 (not column 0).
            candidate_cells = []
            if len(cells) > 2:
                candidate_cells.append(cells[2])
            candidate_cells.extend(cells[:3])
            for c in candidate_cells:
                text = c.get_text(" ", strip=True)
                id_match = re.search(r"\b(\d{5,10})\b", text)
                if id_match:
                    esmo_id = int(id_match.group(1))
                    break
        if not esmo_id:
            return None
        dt_text = cells[1].get_text(" ", strip=True) if len(cells) > 1 else row.get_text(" ", strip=True)
        dt_match = re.search(r"\b\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\b", dt_text)
        timestamp = dt_match.group(0) if dt_match else ""
        terminal_cell = row.select_one("td.terminal")
        if terminal_cell is None and len(cells) > 2:
            # Monitor layout keeps terminal/location in column 2, while compact journal
            # uses column 3 for terminal index. Detect by text shape.
            c2_text = cells[2].get_text(" ", strip=True)
            if re.search(r"(tkm|terminal|majmuasi|avtoxo'jalik|автохозяй|тог)", c2_text, flags=re.IGNORECASE):
                terminal_cell = cells[2]
        if terminal_cell is None and len(cells) > 3:
            terminal_cell = cells[3]
        terminal = terminal_cell.get_text(" ", strip=True) if terminal_cell else ""
        emp_info_cell = row.select_one("td.name")
        if emp_info_cell is None and len(cells) > 4:
            emp_info_cell = cells[4]
        if emp_info_cell is None:
            return None
        emp_link = emp_info_cell.find("a")
        employee_name = emp_link.get_text(strip=True) if emp_link else emp_info_cell.get_text(" ", strip=True)
        # "Propusk: 2034" can be mojibake depending on portal output;
        # use the last numeric token from employee info.
        emp_text = emp_info_cell.get_text(" ", strip=True)
        pass_nums = re.findall(r"\b\d{3,10}\b", emp_text)
        employee_pass_id = pass_nums[-1] if pass_nums else None
        check_cell = row.select_one("td.result")
        if check_cell is None and len(cells) > 8:
            check_cell = cells[8]
        vitals = self._parse_vitals_from_cell(check_cell)
        row_text = row.get_text(" ", strip=True)
        vitals = self._enrich_vitals_from_text(vitals, row_text)
        comment_cell = row.select_one("td.comment")
        comment_text = comment_cell.get_text(" ", strip=True) if comment_cell else ""
        admittance_cell = row.select_one("td.admittance")
        if admittance_cell is None and len(cells) > 10:
            admittance_cell = cells[10]
        admittance_text = admittance_cell.get_text(" ", strip=True) if admittance_cell else ""
        admittance_classes = " ".join(admittance_cell.get("class", [])) if admittance_cell else ""
        result = self._detect_exam_result(
            row_text=row_text,
            comment_text=comment_text,
            admittance_text=admittance_text,
            admittance_classes=admittance_classes,
        )

        # Newer ESMO journal pages can be condensed and miss terminal/result fields.
        # In that case pull MO detail page and backfill critical fields.
        needs_detail = (
            not employee_name
            or not terminal
            or re.fullmatch(r"\d{1,4}", terminal.strip() if terminal else "") is not None
            or re.search(r"\bTKM\s*[1-4]\s*-\s*terminal\b", terminal, flags=re.IGNORECASE) is None
            or result is None
            or employee_pass_id is None
            or vitals.get("pulse") is None
            or vitals.get("temperature") is None
        )
        if needs_detail:
            detail = self._fetch_exam_detail(esmo_id)
            if detail:
                employee_name = employee_name or str(detail.get("employee_name") or "")
                employee_pass_id = employee_pass_id or detail.get("employee_pass_id")
                detail_terminal = str(detail.get("terminal") or "")
                if detail_terminal and (not terminal or re.fullmatch(r"\d{1,4}", terminal.strip())):
                    terminal = detail_terminal
                timestamp = timestamp or str(detail.get("timestamp") or "")
                if result is None:
                    result = detail.get("result")
                if vitals.get("pressure_systolic") is None:
                    vitals["pressure_systolic"] = detail.get("pressure_systolic")
                if vitals.get("pressure_diastolic") is None:
                    vitals["pressure_diastolic"] = detail.get("pressure_diastolic")
                if vitals.get("pulse") is None:
                    vitals["pulse"] = detail.get("pulse")
                if vitals.get("temperature") is None:
                    vitals["temperature"] = detail.get("temperature")
                if vitals.get("alcohol_mg_l") in (None, 0, 0.0):
                    if detail.get("alcohol_mg_l") is not None:
                        vitals["alcohol_mg_l"] = detail.get("alcohol_mg_l")

        return {
            "esmo_id": esmo_id,
            "timestamp": timestamp,
            "terminal": terminal,
            "employee_name": employee_name,
            "employee_pass_id": employee_pass_id,
            "result": result,
            **vitals,
        }

    def _fetch_exam_detail(self, esmo_id: int) -> Dict[str, Any]:
        cached = self._exam_detail_cache.get(esmo_id)
        if cached is not None:
            return cached

        detail: Dict[str, Any] = {
            "employee_name": "",
            "employee_pass_id": None,
            "terminal": "",
            "timestamp": "",
            "result": None,
            "pressure_systolic": None,
            "pressure_diastolic": None,
            "pulse": None,
            "temperature": None,
            "alcohol_mg_l": 0.0,
        }

        try:
            # Main MO card contains terminal/result/vitals in a stable table.
            mo_url = f"{self.base_url}mo/{esmo_id}/"
            mo_resp = self._get(mo_url)
            mo_soup = BeautifulSoup(mo_resp.text, "lxml")
            mo_text = mo_soup.get_text(" ", strip=True)

            terminal_match = re.search(r"TKM\s*[1-4]\s*-\s*terminal(?:\s*\[\d+\])?", mo_text, flags=re.IGNORECASE)
            if terminal_match:
                detail["terminal"] = terminal_match.group(0)
            else:
                terminal_id_match = re.search(r"terminal\s*\[(\d{1,3})\]", mo_text, flags=re.IGNORECASE)
                if terminal_id_match:
                    detail["terminal"] = f"terminal [{terminal_id_match.group(1)}]"

            ts_matches = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\b", mo_text)
            if ts_matches:
                detail["timestamp"] = ts_matches[0]

            # Reuse existing result detector with richer detail text.
            marker_text = " ".join(
                node.get_text(" ", strip=True)
                for node in mo_soup.select("div.mo_status_2, div.dopusk_state_1, div.dopusk_state_0, div.dopusk_comment, td.dopusk_1, td.dopusk_0")
            )
            marker_classes = " ".join(
                " ".join(node.get("class", []))
                for node in mo_soup.select("div.dopusk_state_1, div.dopusk_state_0, td.dopusk_1, td.dopusk_0")
            )
            result = self._detect_exam_result(
                row_text=mo_text,
                comment_text=marker_text,
                admittance_text=marker_text,
                admittance_classes=marker_classes,
            )
            if result is None:
                if mo_soup.select_one("div.dopusk_state_1, td.dopusk_1"):
                    result = "passed"
                elif mo_soup.select_one("div.dopusk_state_0, td.dopusk_0"):
                    result = "failed"
            detail["result"] = result

            # Prefer structured table parsing for vitals: this is stable even when text labels vary.
            table_vitals = self._extract_vitals_from_detail_table(mo_soup)
            detail.update(table_vitals)

            # Fill vitals from full-page text.
            detail.update(self._enrich_vitals_from_text(detail, mo_text))
        except Exception as exc:
            logger.warning("ESMO detail fetch failed for mo_id=%s: %s", esmo_id, exc)

        # Optional fallback: pupilometry page usually carries employee name + pass card number.
        if (not detail.get("employee_name") or not detail.get("employee_pass_id")) and self.origin:
            try:
                pp_url = f"{self.origin}/window/mo/{esmo_id}/pp/"
                pp_resp = self._get(pp_url)
                pp_soup = BeautifulSoup(pp_resp.text, "lxml")
                heading = pp_soup.select_one("#page_title h1")
                if heading:
                    h_text = heading.get_text(" ", strip=True)
                    m_name = re.search(r"сотрудника\s+(.+)$", h_text, flags=re.IGNORECASE)
                    if m_name:
                        detail["employee_name"] = m_name.group(1).strip()

                center_h2 = pp_soup.select_one("h2.center")
                if center_h2:
                    h2_text = center_h2.get_text(" ", strip=True)
                    ts_matches = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\b", h2_text)
                    if ts_matches and not detail.get("timestamp"):
                        detail["timestamp"] = ts_matches[-1]
                    # Pass card number is typically a 3..10 digit token in this heading.
                    nums = [n for n in re.findall(r"\b\d{3,10}\b", h2_text) if n != str(esmo_id)]
                    if nums and not detail.get("employee_pass_id"):
                        detail["employee_pass_id"] = nums[0]
            except Exception as exc:
                logger.debug("ESMO pp detail fallback failed for mo_id=%s: %s", esmo_id, exc)

        self._exam_detail_cache[esmo_id] = detail
        return detail

    def _extract_vitals_from_detail_table(self, soup: BeautifulSoup) -> Dict[str, Any]:
        vitals: Dict[str, Any] = {
            "pressure_systolic": None,
            "pressure_diastolic": None,
            "pulse": None,
            "temperature": None,
            "alcohol_mg_l": 0.0,
        }

        # Typical structure: table.info -> rows with 3 cells (label, value, range).
        values: list[str] = []
        labeled_rows: list[tuple[str, str]] = []
        for tr in soup.select("table.info tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 2:
                continue
            raw_label = tds[0].get_text(" ", strip=True).lower()
            raw_value = tds[1].get_text(" ", strip=True)
            labeled_rows.append((raw_label, raw_value))
            if raw_value:
                values.append(raw_value)

        if not values:
            return vitals

        # Prefer label-based extraction when possible (stable even if numbers overlap).
        for label, value in labeled_rows:
            if vitals["pressure_systolic"] is not None and vitals["pressure_diastolic"] is not None:
                break
            if not re.search(r"(давлен|pressure|bosim)", label, flags=re.IGNORECASE):
                continue
            pair = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", value)
            if pair:
                vitals["pressure_systolic"] = int(pair.group(1))
                vitals["pressure_diastolic"] = int(pair.group(2))

        for label, value in labeled_rows:
            if vitals["pulse"] is not None:
                break
            if not re.search(r"(пульс|pulse|puls)", label, flags=re.IGNORECASE):
                continue
            m = re.search(r"\b(\d{2,3})\b", value)
            if not m:
                continue
            pulse_val = int(m.group(1))
            if 30 <= pulse_val <= 220:
                vitals["pulse"] = pulse_val

        for label, value in labeled_rows:
            if vitals["temperature"] is not None:
                break
            if not re.search(r"(температур|temperature|temp|harorat)", label, flags=re.IGNORECASE):
                continue
            m = re.search(r"\b(\d{2}(?:[.,]\d)?)\b", value)
            if not m:
                continue
            temp_val = float(m.group(1).replace(",", "."))
            if 30.0 <= temp_val <= 45.0:
                vitals["temperature"] = temp_val

        for label, value in labeled_rows:
            if vitals["alcohol_mg_l"] not in (None, 0.0):
                break
            if not re.search(r"(алкогол|alcohol)", label, flags=re.IGNORECASE):
                continue
            m = re.search(r"\b(\d+(?:[.,]\d+)?)\b", value)
            if not m:
                continue
            alcohol_val = float(m.group(1).replace(",", "."))
            if 0.0 < alcohol_val < 10.0:
                vitals["alcohol_mg_l"] = alcohol_val

        # Fallback numeric extraction if labels are missing/broken.
        # Pressure can appear as a pair in one cell or as two separate rows.
        for v in values:
            pair = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", v)
            if pair:
                vitals["pressure_systolic"] = int(pair.group(1))
                vitals["pressure_diastolic"] = int(pair.group(2))
                break

        if vitals["pressure_systolic"] is None or vitals["pressure_diastolic"] is None:
            ints = []
            for v in values:
                m = re.fullmatch(r"\D*(\d{2,3})\D*", v)
                if m:
                    ints.append(int(m.group(1)))
            if len(ints) >= 2:
                vitals["pressure_systolic"] = ints[0]
                vitals["pressure_diastolic"] = ints[1]

        # Pulse: first plausible integer after pressure values.
        for v in values:
            m = re.fullmatch(r"\D*(\d{2,3})\D*", v)
            if not m:
                continue
            n = int(m.group(1))
            if vitals["pressure_systolic"] is not None and n == vitals["pressure_systolic"]:
                continue
            if vitals["pressure_diastolic"] is not None and n == vitals["pressure_diastolic"]:
                continue
            if 30 <= n <= 220:
                vitals["pulse"] = n
                break

        # Temperature: first decimal-like value in human range.
        for v in values:
            m = re.search(r"\b(\d{2}(?:[.,]\d)?)\b", v)
            if not m:
                continue
            temp = float(m.group(1).replace(",", "."))
            if 30.0 <= temp <= 45.0:
                vitals["temperature"] = temp
                break

        # Alcohol (if non-zero provided).
        for v in values:
            m = re.search(r"\b(\d+(?:[.,]\d+)?)\b", v)
            if not m:
                continue
            val = float(m.group(1).replace(",", "."))
            if 0.0 < val < 10.0:
                vitals["alcohol_mg_l"] = val
                break

        return vitals

    def _parse_vitals_from_cell(self, check_cell) -> Dict[str, Any]:
        vitals = {
            "pressure_systolic": None,
            "pressure_diastolic": None,
            "pulse": None,
            "temperature": None,
            "alcohol_mg_l": 0.0,
        }

        if check_cell is None:
            return vitals

        # Preferred path: parse nested table row values by position.
        nested_rows = check_cell.find_all("tr")
        values: list[str] = []
        for row in nested_rows:
            tds = row.find_all("td")
            if len(tds) >= 2:
                values.append(tds[1].get_text(" ", strip=True))

        for val in values:
            pressure_match = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", val)
            if pressure_match:
                vitals["pressure_systolic"] = int(pressure_match.group(1))
                vitals["pressure_diastolic"] = int(pressure_match.group(2))
                break

        for val in values:
            pulse_val = val.strip()
            if pulse_val.isdigit():
                p = int(pulse_val)
                if 30 <= p <= 220:
                    vitals["pulse"] = p
                    break

        for val in values:
            temp_match = re.search(r"\b(\d{2}\.\d)\b", val)
            if temp_match:
                vitals["temperature"] = float(temp_match.group(1))
                break

        # Fallback path: parse from flattened text.
        if vitals["pressure_systolic"] is None or vitals["pulse"] is None or vitals["temperature"] is None:
            text = check_cell.get_text(" ", strip=True)

            if vitals["pressure_systolic"] is None:
                pressure_match = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", text)
                if pressure_match:
                    vitals["pressure_systolic"] = int(pressure_match.group(1))
                    vitals["pressure_diastolic"] = int(pressure_match.group(2))

            if vitals["temperature"] is None:
                temp_match = re.search(r"\b(\d{2}\.\d)\b", text)
                if temp_match:
                    vitals["temperature"] = float(temp_match.group(1))

            if vitals["pulse"] is None:
                nums = [int(n) for n in re.findall(r"\b\d{2,3}\b", text)]
                if nums:
                    # Ignore pressure numbers if present and pick the first plausible pulse.
                    for n in nums:
                        if 30 <= n <= 220:
                            vitals["pulse"] = n
                            break

        return vitals

    def _detect_manual_review(self, row_text: str, decision_text: str) -> bool:
        text = f"{row_text} {decision_text}".lower()
        return (
            "\u0440\u0443\u0447\u043d\u0430\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430" in text
            or "manual check" in text
            or "manual review" in text
        )

    def _detect_exam_result(
        self,
        row_text: str,
        comment_text: str,
        admittance_text: str,
        admittance_classes: str,
    ) -> Optional[str]:
        blob = " ".join(
            part for part in [row_text, comment_text, admittance_text, admittance_classes] if part
        ).lower()
        if self._detect_manual_review(blob, ""):
            return "review"
        has_pass_class = "dopusk_1" in admittance_classes or "dopusk_state_1" in admittance_classes
        has_fail_class = "dopusk_0" in admittance_classes or "dopusk_state_0" in admittance_classes
        positive_markers = (
            "\u043e\u0441\u043c\u043e\u0442\u0440 \u043e\u043a\u043e\u043d\u0447\u0435\u043d, \u043f\u043e\u043b\u043e\u0436",
            "\u043e\u0441\u043c\u043e\u0442\u0440 \u043e\u043a\u043e\u043d\u0447\u0435\u043d \u043f\u043e\u043b\u043e\u0436",
            "\u0434\u043e\u043f\u0443\u0441\u043a \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d",
            "\u0434\u043e\u043f\u0443\u0441\u043a \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d",
        )
        negative_markers = (
            "\u043d\u0435\u0434\u043e\u043f\u0443\u0441\u043a",
            "\u0434\u043e\u043f\u0443\u0441\u043a \u0437\u0430\u043f\u0440\u0435\u0449",
            "\u043d\u0435 \u0434\u043e\u043f\u0443\u0449",
            "\u043e\u0441\u043c\u043e\u0442\u0440 \u043d\u0435 \u043f\u0440\u043e\u0439\u0434\u0435\u043d",
            "\u043f\u043e\u0432\u044b\u0448\u0435\u043d\u043d\u043e\u0435",
            "\u043f\u043e\u043d\u0438\u0436\u0435\u043d\u043d\u043e\u0435",
            "\u043e\u0442\u043a\u0430\u0437",
            "\u043e\u0442\u043a\u043b\u043e\u043d",
        )
        has_positive_text = any(m in blob for m in positive_markers)
        has_negative_text = any(m in blob for m in negative_markers)
        if has_positive_text and not has_negative_text:
            return "passed"
        if has_negative_text and not has_positive_text:
            return "failed"
        if has_pass_class and not has_fail_class:
            return "passed"
        if has_fail_class and not has_pass_class:
            return "failed"
        # Unknown/incomplete row; don't force "failed" because that can overwrite
        # already-correct "passed" values from previous poll iterations.
        return None

    def _enrich_vitals_from_text(self, vitals: Dict[str, Any], text: str) -> Dict[str, Any]:
        if not text:
            return vitals

        # Pressure
        if vitals["pressure_systolic"] is None or vitals["pressure_diastolic"] is None:
            pressure_match = re.search(
                r"(?:Р°СЂС‚РµСЂРёР°Р»[Р°-СЏ]*\s+РґР°РІР»РµРЅ[Р°-СЏ]*|blood pressure|РґР°РІР»РµРЅ[Р°-СЏ]*|bp)[^\d]{0,20}(\d{2,3})\s*/\s*(\d{2,3})",
                text,
                flags=re.IGNORECASE,
            )
            if pressure_match:
                vitals["pressure_systolic"] = int(pressure_match.group(1))
                vitals["pressure_diastolic"] = int(pressure_match.group(2))
            else:
                generic_pressure = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", text)
                if generic_pressure:
                    vitals["pressure_systolic"] = int(generic_pressure.group(1))
                    vitals["pressure_diastolic"] = int(generic_pressure.group(2))

        # Pulse
        if vitals["pulse"] is None:
            pulse_match = re.search(r"(?:РїСѓР»СЊСЃ|pulse)[^\d]{0,20}(\d{2,3})\b", text, flags=re.IGNORECASE)
            if pulse_match:
                vitals["pulse"] = int(pulse_match.group(1))

        # Temperature
        if vitals["temperature"] is None:
            temp_match = re.search(r"(?:С‚РµРјРїРµСЂР°С‚СѓСЂ[Р°-СЏ]*|temperature|temp)[^\d]{0,20}(\d{2}(?:[.,]\d)?)\b", text, flags=re.IGNORECASE)
            if temp_match:
                vitals["temperature"] = float(temp_match.group(1).replace(",", "."))

        return vitals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = EsmoClient()
    print("login:", client.login())
    employees = client.fetch_employees()
    exams = client.fetch_latest_exams()
    print("employees:", len(employees))
    print("exams:", len(exams))

