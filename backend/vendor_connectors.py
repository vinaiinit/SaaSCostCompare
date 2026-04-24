"""
Vendor API connectors for pulling real-time license utilization data.
Each connector authenticates with the vendor's API and retrieves
license counts, active users, and usage metrics.
"""
import os
import json
import base64
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

        # JWT bearer flow (most secure — certificate-based, no password)
        if credentials.get("private_key") and credentials.get("client_id") and credentials.get("username"):
            return self._jwt_bearer_login(credentials)

        # Username-password OAuth flow (fallback)
        if credentials.get("client_id") and credentials.get("username") and credentials.get("password"):
            return self._oauth_login(credentials)

        return False

    def _jwt_bearer_login(self, credentials: dict) -> bool:
        import requests
        import jwt
        import time

        # JWT bearer must always go through login.salesforce.com, not custom domains
        audience = "https://login.salesforce.com"
        token_endpoint = "https://login.salesforce.com/services/oauth2/token"

        private_key = credentials.get("private_key", "")
        # Handle escaped newlines from form input
        if "\\n" in private_key:
            private_key = private_key.replace("\\n", "\n")

        now = int(time.time())
        payload = {
            "iss": credentials.get("client_id", ""),
            "sub": credentials.get("username", ""),
            "aud": audience,
            "exp": now + 180,
        }

        try:
            assertion = jwt.encode(payload, private_key, algorithm="RS256")

            resp = requests.post(
                token_endpoint,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data["access_token"]
                self.instance_url = data["instance_url"]
                print(f"Salesforce JWT bearer login successful: {self.instance_url}")
                return True

            print(f"Salesforce JWT bearer login failed: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return False

        except Exception as e:
            import traceback
            print(f"Salesforce JWT bearer error: {e}")
            traceback.print_exc()
            return False

    def _oauth_login(self, credentials: dict) -> bool:
        import requests

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
    """Connect to SAP S/4HANA Cloud APIs to pull license and user data."""

    vendor_name = "SAP"

    def __init__(self):
        self.access_token = None
        self.base_url = None
        self.demo_mode = False

    def authenticate(self, credentials: dict) -> bool:
        import requests

        # Demo mode for testing without a real SAP system
        if credentials.get("demo_mode"):
            self.demo_mode = True
            return True

        self.base_url = credentials.get("base_url", "").strip().rstrip("/")
        if not self.base_url:
            return False

        # Basic auth (username + password)
        if credentials.get("username") and credentials.get("password"):
            self._auth_header = {
                "Authorization": "Basic " + base64.standard_b64encode(
                    f"{credentials['username']}:{credentials['password']}".encode()
                ).decode()
            }
            return self._verify_connection()

        # OAuth 2.0 client credentials (Communication Arrangement)
        token_url = credentials.get("token_url", "").strip()
        client_id = credentials.get("client_id", "")
        client_secret = credentials.get("client_secret", "")

        if token_url and client_id and client_secret:
            try:
                resp = requests.post(
                    token_url,
                    data={"grant_type": "client_credentials"},
                    auth=(client_id, client_secret),
                    timeout=15,
                )
                if resp.status_code == 200:
                    self.access_token = resp.json().get("access_token")
                    self._auth_header = {"Authorization": f"Bearer {self.access_token}"}
                    return self._verify_connection()
                print(f"SAP OAuth failed: {resp.status_code} {resp.text[:300]}")
            except Exception as e:
                print(f"SAP OAuth error: {e}")
            return False

        return False

    def _verify_connection(self) -> bool:
        import requests
        try:
            resp = requests.get(
                f"{self.base_url}/sap/opu/odata/sap/API_BUSINESS_USER/User?$top=1&$format=json",
                headers=self._auth_header,
                timeout=10,
                verify=True,
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"SAP connection verify failed: {e}")
            return False

    def _odata_get(self, path: str, params: dict = None) -> dict:
        import requests
        url = f"{self.base_url}{path}"
        default_params = {"$format": "json"}
        if params:
            default_params.update(params)
        try:
            resp = requests.get(
                url,
                headers=self._auth_header,
                params=default_params,
                timeout=15,
                verify=True,
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"SAP OData request failed: {resp.status_code} {url}")
        except Exception as e:
            print(f"SAP OData error: {e}")
        return {}

    def get_license_summary(self) -> dict:
        if self.demo_mode:
            return self._get_demo_data()

        licenses = self._get_user_licenses()
        login_activity = self._get_login_activity()

        return {
            "vendor": "SAP",
            "licenses": licenses,
            "login_activity": login_activity,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    def _get_user_licenses(self) -> list:
        # Get all business users and categorize by license type
        data = self._odata_get(
            "/sap/opu/odata/sap/API_BUSINESS_USER/User",
            {"$select": "UserName,UserID,IsLocked,ValidityStartDate,ValidityEndDate"}
        )
        results = data.get("d", {}).get("results", [])

        total_users = len(results)
        active_users = sum(1 for u in results if not u.get("IsLocked", False))
        locked_users = total_users - active_users

        # Get role assignments to determine license types
        role_data = self._odata_get(
            "/sap/opu/odata/sap/API_BUSINESS_USER/UserAssignment",
            {"$select": "UserID,RoleID"}
        )
        role_results = role_data.get("d", {}).get("results", [])
        users_with_roles = set(r.get("UserID") for r in role_results)

        # SAP license types based on usage patterns
        licenses = []

        # Professional users (users with business roles)
        prof_count = len(users_with_roles)
        licenses.append({
            "product_name": "SAP S/4HANA Professional User",
            "total_licenses": prof_count,
            "assigned_licenses": prof_count,
            "active_users": min(prof_count, active_users),
            "unused_licenses": 0,
            "utilization_pct": round(min(prof_count, active_users) / max(prof_count, 1) * 100, 1),
        })

        # Limited Professional (users without specific roles)
        limited_count = max(total_users - prof_count, 0)
        if limited_count > 0:
            licenses.append({
                "product_name": "SAP S/4HANA Limited Professional User",
                "total_licenses": limited_count,
                "assigned_licenses": limited_count,
                "active_users": max(active_users - prof_count, 0),
                "unused_licenses": locked_users,
                "utilization_pct": round((limited_count - locked_users) / max(limited_count, 1) * 100, 1),
            })

        # Overall summary
        licenses.insert(0, {
            "product_name": "All SAP Named Users (Total)",
            "total_licenses": total_users,
            "assigned_licenses": total_users,
            "active_users": active_users,
            "unused_licenses": locked_users,
            "utilization_pct": round(active_users / max(total_users, 1) * 100, 1),
        })

        return licenses

    def _get_login_activity(self) -> dict:
        # Get active users count from business user API
        data = self._odata_get(
            "/sap/opu/odata/sap/API_BUSINESS_USER/User",
            {"$filter": "IsLocked eq false", "$inlinecount": "allpages", "$top": "1"}
        )

        total_active = int(data.get("d", {}).get("__count", 0))

        all_data = self._odata_get(
            "/sap/opu/odata/sap/API_BUSINESS_USER/User",
            {"$inlinecount": "allpages", "$top": "1"}
        )
        total_users = int(all_data.get("d", {}).get("__count", 0))

        return {
            "daily_avg_logins": 0,
            "unique_users_30d": total_active,
            "total_users": total_users,
        }

    def _get_demo_data(self) -> dict:
        """Realistic demo data for SAP S/4HANA license analysis."""
        return {
            "vendor": "SAP",
            "demo_mode": True,
            "licenses": [
                {
                    "product_name": "All SAP Named Users (Total)",
                    "total_licenses": 850,
                    "assigned_licenses": 850,
                    "active_users": 680,
                    "unused_licenses": 170,
                    "utilization_pct": 80.0,
                },
                {
                    "product_name": "SAP S/4HANA Professional User",
                    "total_licenses": 320,
                    "assigned_licenses": 320,
                    "active_users": 285,
                    "unused_licenses": 35,
                    "utilization_pct": 89.1,
                },
                {
                    "product_name": "SAP S/4HANA Limited Professional User",
                    "total_licenses": 280,
                    "assigned_licenses": 280,
                    "active_users": 195,
                    "unused_licenses": 85,
                    "utilization_pct": 69.6,
                },
                {
                    "product_name": "SAP Developer User",
                    "total_licenses": 50,
                    "assigned_licenses": 50,
                    "active_users": 42,
                    "unused_licenses": 8,
                    "utilization_pct": 84.0,
                },
                {
                    "product_name": "SAP SuccessFactors Employee Central",
                    "total_licenses": 1200,
                    "assigned_licenses": 1100,
                    "active_users": 980,
                    "unused_licenses": 220,
                    "utilization_pct": 81.7,
                },
                {
                    "product_name": "SAP Concur Expense",
                    "total_licenses": 500,
                    "assigned_licenses": 430,
                    "active_users": 310,
                    "unused_licenses": 190,
                    "utilization_pct": 62.0,
                },
                {
                    "product_name": "SAP Analytics Cloud",
                    "total_licenses": 100,
                    "assigned_licenses": 85,
                    "active_users": 52,
                    "unused_licenses": 48,
                    "utilization_pct": 52.0,
                },
            ],
            "login_activity": {
                "daily_avg_logins": 425,
                "unique_users_30d": 680,
                "total_users": 850,
            },
            "retrieved_at": datetime.utcnow().isoformat(),
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
