"""
Hikvision ISAPI Client — READ-ONLY access to turnstile access control events.

This module communicates with Hikvision DS-K1T671M terminals via ISAPI (HTTP GET).
It NEVER writes, modifies, or deletes any data on the turnstile devices.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger("hikvision")


class HikvisionClient:
    """Read-only ISAPI client for a single Hikvision device."""

    def __init__(self, host: str, port: int = 80, user: str = "admin", password: str = "", timeout: int = 10):
        self.base_url = f"http://{host}:{port}"
        self.auth = HTTPDigestAuth(user, password)
        self.timeout = timeout
        self.name = host

    def _get(self, path: str) -> requests.Response | None:
        """Send a READ-ONLY GET request. Never sends POST/PUT/DELETE."""
        try:
            resp = requests.get(
                f"{self.base_url}{path}",
                auth=self.auth,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            logger.warning("Hikvision GET %s%s failed: %s", self.base_url, path, exc)
            return None

    def _post_search(self, path: str, body: dict) -> requests.Response | None:
        """Send a POST request for SEARCH operations only (read-only search).
        Hikvision ISAPI uses POST for search queries — this does NOT modify any data."""
        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                json=body,
                auth=self.auth,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            logger.warning("Hikvision POST-search %s%s failed: %s", self.base_url, path, exc)
            return None

    def get_device_info(self) -> dict | None:
        """GET /ISAPI/System/deviceInfo — read device information."""
        resp = self._get("/ISAPI/System/deviceInfo")
        if resp is None:
            return None
        # Parse XML response
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            ns = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}
            info: dict[str, Any] = {}
            for child in root:
                tag = child.tag.replace(f"{{{ns.get('hik', '')}}}", "").split("}")[-1]
                info[tag] = child.text
            return info
        except Exception as exc:
            logger.warning("Failed to parse deviceInfo: %s", exc)
            return None

    def check_connection(self) -> bool:
        """Check if device is reachable and ISAPI responds."""
        info = self.get_device_info()
        return info is not None

    def fetch_access_events(self, start_time: str, end_time: str) -> list[dict]:
        """
        Fetch access control events (read-only search).

        Hikvision ISAPI uses POST /ISAPI/AccessControl/AcsEvent?format=json
        for SEARCHING events. Despite being POST, this is a READ-ONLY query.
        It does NOT create, modify, or delete any data on the device.

        Args:
            start_time: ISO format "2026-02-13T00:00:00+05:00"
            end_time: ISO format "2026-02-13T23:59:59+05:00"

        Returns:
            List of event dicts with keys like: employeeNoString, time, eventType, etc.
        """
        all_events: list[dict] = []
        search_position = 0
        max_results = 30  # Per-page

        while True:
            body = {
                "AcsEventCond": {
                    "searchID": "minetrack_readonly_search",
                    "searchResultPosition": search_position,
                    "maxResults": max_results,
                    "major": 0,
                    "minor": 0,
                    "startTime": start_time,
                    "endTime": end_time,
                }
            }

            resp = self._post_search(
                "/ISAPI/AccessControl/AcsEvent?format=json",
                body,
            )

            if resp is None:
                break

            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError):
                logger.warning("Invalid JSON from AcsEvent search")
                break

            acs_event = data.get("AcsEvent", {})
            total_matches = acs_event.get("totalMatches", 0)
            info_list = acs_event.get("InfoList", [])

            if not info_list:
                break

            all_events.extend(info_list)
            search_position += len(info_list)

            if search_position >= total_matches:
                break

        logger.info("Fetched %d events from %s", len(all_events), self.name)
        return all_events
