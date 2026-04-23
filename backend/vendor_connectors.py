"""
Vendor API connectors for pulling real-time license utilization data.
Each connector authenticates with the vendor's API and retrieves
license counts, active users, and usage metrics.
"""
import os
import json
from datetime import datetime, timedelta
from abc import ABC, abstractmethod


class VendorConnector(ABC):
    """Base class for vendor API connectors."""

    vendor_name: str = ""

    @abstractmethod
    def authenticate(self, credentials: dict) -> bool:
        """Authenticate with the vendor API. Returns True on success."""
        ...

    @abstractmethod
    def get_license_summary(self) -> dict:
        """
        Return license utilization summary:
        {
            "vendor": str,
            "licenses": [
                {
                    "product_name": str,
                    "total_licenses": int,
                    "assigned_licenses": int,
                    "active_users": int,
                    "unused_licenses": int,
                    "utilization_pct": float,
                }
            ],
            "login_activity": {
                "daily_avg_logins": int,
                "unique_users_30d": int,
                "total_users": int,
            },
            "retrieved_at": str,
        }
        """
        ...


class SalesforceConnector(VendorConnector):
    """Connect to Salesforce REST API to pull license data."""

    vendor_name = "Salesforce"

    def __init__(self):
        self.instance_url = None
        self.access_token = None
        self.api_version = "v59.0"

    def authenticate(self, credentials: dict) -> bool:
        import requests

        # Direct access token (pre-authenticated)
        if credentials.get("access_token") and credentials.get("instance_url"):
            self.access_token = credentials["access_token"]
            self.instance_url = credentials["instance_url"].rstrip("/")
            return self._verify_connection()

        # Connected App OAuth (username-password flow)
        if credentials.get("client_id") and credentials.get("username"):
            return self._oauth_login(credentials)

        return False

    def _oauth_login(self, credentials: dict) -> bool:
        import requests

        # Try custom login URL first, then standard endpoints
        login_url = credentials.get("login_url", "").strip().rstrip("/")
        urls_to_try = []
        if login_url:
            urls_to_try.append(f"{login_url}/services/oauth2/token")
        urls_to_try.append("https://login.salesforce.com/services/oauth2/token")

        payload = {
            "grant_type": "password",
            "client_id": credentials.get("client_id", ""),
            "client_secret": credentials.get("client_secret", ""),
            "username": credentials.get("username", ""),
            "password": credentials.get("password", ""),
        }

        for token_url in urls_to_try:
            try:
                resp = requests.post(token_url, data=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    self.access_token = data["access_token"]
                    self.instance_url = data["instance_url"]
                    print(f"Salesforce OAuth login successful: {self.instance_url}")
                    return True
                print(f"Salesforce OAuth failed at {token_url}: {resp.status_code}")
                print(f"Response: {resp.text[:500]}")
            except Exception as e:
                print(f"Salesforce OAuth error at {token_url}: {e}")

        return False

    def _verify_connection(self) -> bool:
        import requests
        try:
            resp = requests.get(
                f"{self.instance_url}/services/data/{self.api_version}/limits/",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _query(self, soql: str) -> list:
        import requests
        url = f"{self.instance_url}/services/data/{self.api_version}/query/"
        resp = requests.get(
            url,
            params={"q": soql},
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"Salesforce query failed: {resp.status_code} {resp.text[:200]}")
            return []
        return resp.json().get("records", [])

    def get_license_summary(self) -> dict:
        licenses = self._get_user_licenses()
        login_activity = self._get_login_activity()

        return {
            "vendor": "Salesforce",
            "licenses": licenses,
            "login_activity": login_activity,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    def _get_user_licenses(self) -> list:
        records = self._query(
            "SELECT Name, TotalLicenses, UsedLicenses "
            "FROM UserLicense "
            "WHERE TotalLicenses > 0"
        )
        licenses = []
        for r in records:
            total = r.get("TotalLicenses", 0) or 0
            used = r.get("UsedLicenses", 0) or 0
            unused = max(total - used, 0)
            util = round((used / total * 100), 1) if total > 0 else 0

            licenses.append({
                "product_name": r.get("Name", "Unknown"),
                "total_licenses": total,
                "assigned_licenses": used,
                "active_users": used,
                "unused_licenses": unused,
                "utilization_pct": util,
            })
        return licenses

    def _get_login_activity(self) -> dict:
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")

        login_records = self._query(
            f"SELECT COUNT(Id) cnt, COUNT_DISTINCT(UserId) unique_users "
            f"FROM LoginHistory "
            f"WHERE LoginTime >= {thirty_days_ago}"
        )

        total_logins = 0
        unique_users = 0
        if login_records:
            total_logins = login_records[0].get("cnt", 0) or 0
            unique_users = login_records[0].get("unique_users", 0) or 0

        total_users_records = self._query(
            "SELECT COUNT(Id) cnt FROM User WHERE IsActive = true"
        )
        total_users = total_users_records[0].get("cnt", 0) if total_users_records else 0

        return {
            "daily_avg_logins": round(total_logins / 30) if total_logins else 0,
            "unique_users_30d": unique_users,
            "total_users": total_users,
        }


class MicrosoftConnector(VendorConnector):
    """Connect to Microsoft Graph API to pull M365/Azure license data."""

    vendor_name = "Microsoft"

    def __init__(self):
        self.access_token = None
        self.tenant_id = None

    def authenticate(self, credentials: dict) -> bool:
        import requests

        if credentials.get("access_token"):
            self.access_token = credentials["access_token"]
            return self._verify_connection()

        self.tenant_id = credentials.get("tenant_id", "")
        client_id = credentials.get("client_id", "")
        client_secret = credentials.get("client_secret", "")

        if not all([self.tenant_id, client_id, client_secret]):
            return False

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        try:
            resp = requests.post(token_url, data=payload, timeout=15)
            if resp.status_code == 200:
                self.access_token = resp.json()["access_token"]
                return True
            print(f"Microsoft auth failed: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            print(f"Microsoft auth error: {e}")
            return False

    def _verify_connection(self) -> bool:
        import requests
        try:
            resp = requests.get(
                "https://graph.microsoft.com/v1.0/organization",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _get(self, path: str) -> dict:
        import requests
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0{path}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"Microsoft Graph failed: {resp.status_code} {resp.text[:200]}")
            return {}
        return resp.json()

    def get_license_summary(self) -> dict:
        licenses = self._get_subscribed_skus()
        login_activity = self._get_sign_in_activity()

        return {
            "vendor": "Microsoft (M365/Azure)",
            "licenses": licenses,
            "login_activity": login_activity,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    def _get_subscribed_skus(self) -> list:
        data = self._get("/subscribedSkus")
        skus = data.get("value", [])

        # Friendly names for common SKU part numbers
        sku_names = {
            "O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
            "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Standard",
            "ENTERPRISEPACK": "Office 365 E3",
            "ENTERPRISEPREMIUM": "Office 365 E5",
            "SPE_E3": "Microsoft 365 E3",
            "SPE_E5": "Microsoft 365 E5",
            "FLOW_FREE": "Power Automate Free",
            "POWER_BI_STANDARD": "Power BI Free",
            "POWER_BI_PRO": "Power BI Pro",
            "TEAMS_EXPLORATORY": "Teams Exploratory",
            "VISIOCLIENT": "Visio Plan 2",
            "PROJECTPREMIUM": "Project Plan 5",
            "EMS_E3": "Enterprise Mobility + Security E3",
            "EMS_E5": "Enterprise Mobility + Security E5",
            "ATP_ENTERPRISE": "Microsoft Defender for Office 365 P1",
            "WIN_DEF_ATP": "Microsoft Defender for Endpoint",
        }

        licenses = []
        for sku in skus:
            if sku.get("capabilityStatus") != "Enabled":
                continue

            part_number = sku.get("skuPartNumber", "")
            display_name = sku_names.get(part_number, part_number)

            total = 0
            for unit in sku.get("prepaidUnits", {}).values():
                if isinstance(unit, int):
                    total += unit

            consumed = sku.get("consumedUnits", 0)
            unused = max(total - consumed, 0)
            util = round((consumed / total * 100), 1) if total > 0 else 0

            licenses.append({
                "product_name": display_name,
                "total_licenses": total,
                "assigned_licenses": consumed,
                "active_users": consumed,
                "unused_licenses": unused,
                "utilization_pct": util,
            })

        return licenses

    def _get_sign_in_activity(self) -> dict:
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")

        data = self._get(
            f"/auditLogs/signIns?$filter=createdDateTime ge {thirty_days_ago}&$top=1&$count=true"
        )
        total_logins = data.get("@odata.count", 0)

        users_data = self._get("/users?$count=true&$top=1")
        total_users = users_data.get("@odata.count", 0)

        return {
            "daily_avg_logins": round(total_logins / 30) if total_logins else 0,
            "unique_users_30d": 0,
            "total_users": total_users,
        }


class SAPConnector(VendorConnector):
    """Placeholder connector for SAP license data."""

    vendor_name = "SAP"

    def __init__(self):
        self.access_token = None
        self.base_url = None

    def authenticate(self, credentials: dict) -> bool:
        self.base_url = credentials.get("base_url", "").rstrip("/")
        self.access_token = credentials.get("access_token", "")
        if not self.base_url or not self.access_token:
            return False
        return True

    def get_license_summary(self) -> dict:
        return {
            "vendor": "SAP",
            "licenses": [],
            "login_activity": {"daily_avg_logins": 0, "unique_users_30d": 0, "total_users": 0},
            "retrieved_at": datetime.utcnow().isoformat(),
            "note": "SAP license analysis requires SAP License Administration Workbench (LAW) access. Full integration coming soon.",
        }


class OracleConnector(VendorConnector):
    """Placeholder connector for Oracle license data."""

    vendor_name = "Oracle"

    def authenticate(self, credentials: dict) -> bool:
        return bool(credentials.get("access_token") or credentials.get("username"))

    def get_license_summary(self) -> dict:
        return {
            "vendor": "Oracle",
            "licenses": [],
            "login_activity": {"daily_avg_logins": 0, "unique_users_30d": 0, "total_users": 0},
            "retrieved_at": datetime.utcnow().isoformat(),
            "note": "Oracle license analysis via Oracle Cloud Infrastructure API. Full integration coming soon.",
        }


class GoogleCloudConnector(VendorConnector):
    """Placeholder connector for Google Cloud/Workspace license data."""

    vendor_name = "Google Cloud"

    def authenticate(self, credentials: dict) -> bool:
        return bool(credentials.get("access_token") or credentials.get("service_account_key"))

    def get_license_summary(self) -> dict:
        return {
            "vendor": "Google Cloud",
            "licenses": [],
            "login_activity": {"daily_avg_logins": 0, "unique_users_30d": 0, "total_users": 0},
            "retrieved_at": datetime.utcnow().isoformat(),
            "note": "Google Workspace license analysis via Admin SDK. Full integration coming soon.",
        }


class AWSConnector(VendorConnector):
    """Placeholder connector for AWS license/usage data."""

    vendor_name = "AWS"

    def authenticate(self, credentials: dict) -> bool:
        return bool(credentials.get("access_key_id") and credentials.get("secret_access_key"))

    def get_license_summary(self) -> dict:
        return {
            "vendor": "AWS",
            "licenses": [],
            "login_activity": {"daily_avg_logins": 0, "unique_users_30d": 0, "total_users": 0},
            "retrieved_at": datetime.utcnow().isoformat(),
            "note": "AWS usage analysis via Cost Explorer and IAM APIs. Full integration coming soon.",
        }


VENDOR_CONNECTORS = {
    "Salesforce": SalesforceConnector,
    "Microsoft (M365/Azure)": MicrosoftConnector,
    "SAP": SAPConnector,
    "Oracle": OracleConnector,
    "Google Cloud": GoogleCloudConnector,
    "AWS": AWSConnector,
}


def get_connector(vendor_name: str) -> VendorConnector | None:
    connector_cls = VENDOR_CONNECTORS.get(vendor_name)
    if connector_cls:
        return connector_cls()
    return None
