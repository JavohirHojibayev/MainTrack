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
        Scrape latest medical exams from available ESMO views.
        """
        if not self.is_logged_in and not self.login():
            return []

        candidates = [
            f"{self.base_url}monitor/",
            f"{self.base_url}monitor/index.php",
            f"{self.base_url}pp/journal/",
            f"{self.base_url}pp/journal/page_1.html",
            # Legacy endpoint from older builds (kept as last fallback).
            f"{self.base_url}monitor/monitor_ws.php",
        ]

        for url in candidates:
            try:
                resp = self._get(url)
                soup = BeautifulSoup(resp.text, "lxml")
                rows = soup.find_all("tr", class_="item")
                if not rows:
                    continue

                exams: list[dict[str, Any]] = []
                for row in rows:
                    parsed = self._parse_exam_row(row)
                    if parsed:
                        exams.append(parsed)

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
            terminal_cell = cells[2]
        terminal = terminal_cell.get_text(" ", strip=True) if terminal_cell else ""
        emp_info_cell = row.select_one("td.name")
        if emp_info_cell is None and len(cells) > 4:
            emp_info_cell = cells[4]
        if emp_info_cell is None:
            return None
        emp_link = emp_info_cell.find("a")
        employee_name = emp_link.get_text(strip=True) if emp_link else ""
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
        return {
            "esmo_id": esmo_id,
            "timestamp": timestamp,
            "terminal": terminal,
            "employee_name": employee_name,
            "employee_pass_id": employee_pass_id,
            "result": result,
            **vitals,
        }

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

