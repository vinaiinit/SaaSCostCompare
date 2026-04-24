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
    """Connect to Google Cloud APIs for compute, disk, and IAM analysis."""

    vendor_name = "Google Cloud"

    def __init__(self):
        self.access_token = None
        self.project_id = None
        self.demo_mode = False

    def authenticate(self, credentials: dict) -> bool:
        import requests
        import jwt
        import time

        if credentials.get("demo_mode"):
            self.demo_mode = True
            return True

        sa_key_raw = credentials.get("service_account_key", "").strip()
        if not sa_key_raw:
            return False

        try:
            sa_key = json.loads(sa_key_raw)
        except json.JSONDecodeError:
            print("Google Cloud: invalid service account JSON")
            return False

        self.project_id = sa_key.get("project_id")
        client_email = sa_key.get("client_email")
        private_key = sa_key.get("private_key", "")
        token_uri = sa_key.get("token_uri", "https://oauth2.googleapis.com/token")

        if not all([self.project_id, client_email, private_key]):
            return False

        now = int(time.time())
        payload = {
            "iss": client_email,
            "sub": client_email,
            "aud": token_uri,
            "iat": now,
            "exp": now + 3600,
            "scope": "https://www.googleapis.com/auth/cloud-platform",
        }

        try:
            assertion = jwt.encode(payload, private_key, algorithm="RS256")
            resp = requests.post(
                token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                self.access_token = resp.json()["access_token"]
                return True
            print(f"Google Cloud auth failed: {resp.status_code} {resp.text[:300]}")
            return False
        except Exception as e:
            print(f"Google Cloud auth error: {e}")
            return False

    def _get(self, url: str) -> dict:
        import requests
        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"GCP API failed: {resp.status_code} {url}")
        except Exception as e:
            print(f"GCP API error: {e}")
        return {}

    def get_license_summary(self) -> dict:
        if self.demo_mode:
            return self._get_demo_data()

        compute = self._get_compute_instances()
        disks = self._get_disk_waste()
        iam = self._get_iam_summary()
        billing = self._get_billing_info()

        licenses = []
        for svc in billing:
            licenses.append({
                "product_name": svc["service"],
                "total_licenses": 0,
                "assigned_licenses": 0,
                "active_users": 0,
                "unused_licenses": 0,
                "utilization_pct": 0,
                "monthly_cost": svc["monthly_cost"],
            })

        return {
            "vendor": "Google Cloud",
            "report_type": "cloud_cost",
            "cost_summary": {
                "total_monthly": sum(s["monthly_cost"] for s in billing),
                "top_services": billing[:10],
            },
            "compute": compute,
            "disk_waste": disks,
            "iam_summary": iam,
            "licenses": licenses[:10],
            "login_activity": {
                "daily_avg_logins": 0,
                "unique_users_30d": iam.get("active_service_accounts", 0),
                "total_users": iam.get("total_service_accounts", 0),
            },
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    def _get_compute_instances(self) -> dict:
        base = f"https://compute.googleapis.com/compute/v1/projects/{self.project_id}"
        data = self._get(f"{base}/aggregated/instances")

        running = 0
        stopped = 0
        total = 0
        machine_types = {}

        for zone_data in data.get("items", {}).values():
            for inst in zone_data.get("instances", []):
                total += 1
                status = inst.get("status", "")
                if status == "RUNNING":
                    running += 1
                elif status in ("TERMINATED", "STOPPED", "SUSPENDED"):
                    stopped += 1

                mt = inst.get("machineType", "").rsplit("/", 1)[-1]
                machine_types[mt] = machine_types.get(mt, 0) + 1

        return {
            "total_instances": total,
            "running": running,
            "stopped": stopped,
            "machine_types": dict(sorted(machine_types.items(), key=lambda x: -x[1])[:10]),
        }

    def _get_disk_waste(self) -> dict:
        base = f"https://compute.googleapis.com/compute/v1/projects/{self.project_id}"
        data = self._get(f"{base}/aggregated/disks")

        unattached = 0
        unattached_size_gb = 0
        total_disks = 0

        for zone_data in data.get("items", {}).values():
            for disk in zone_data.get("disks", []):
                total_disks += 1
                if not disk.get("users"):
                    unattached += 1
                    unattached_size_gb += int(disk.get("sizeGb", 0))

        return {
            "total_disks": total_disks,
            "unattached_disks": unattached,
            "unattached_size_gb": unattached_size_gb,
            "estimated_waste": round(unattached_size_gb * 0.04, 2),  # ~$0.04/GB/month pd-standard
        }

    def _get_iam_summary(self) -> dict:
        url = f"https://iam.googleapis.com/v1/projects/{self.project_id}/serviceAccounts"
        data = self._get(url)
        accounts = data.get("accounts", [])

        total_sa = len(accounts)
        disabled = sum(1 for a in accounts if a.get("disabled"))
        old_keys = 0
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)

        for sa in accounts:
            if sa.get("disabled"):
                continue
            email = sa.get("email", "")
            keys_url = f"https://iam.googleapis.com/v1/projects/{self.project_id}/serviceAccounts/{email}/keys"
            keys_data = self._get(keys_url)
            for key in keys_data.get("keys", []):
                if key.get("keyType") != "USER_MANAGED":
                    continue
                created = key.get("validAfterTime", "")
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                        if created_dt < ninety_days_ago:
                            old_keys += 1
                    except Exception:
                        pass

        return {
            "total_service_accounts": total_sa,
            "active_service_accounts": total_sa - disabled,
            "disabled_service_accounts": disabled,
            "old_sa_keys": old_keys,
        }

    def _get_billing_info(self) -> list:
        # The Cloud Billing API requires billing account access and BigQuery export
        # for detailed cost breakdown. We return basic project-level info here.
        url = f"https://cloudbilling.googleapis.com/v1/projects/{self.project_id}/billingInfo"
        data = self._get(url)
        if data.get("billingAccountName"):
            return [{"service": "Project billing active", "monthly_cost": 0, "total_6m": 0, "trend_6m": []}]
        return []

    def _get_demo_data(self) -> dict:
        return {
            "vendor": "Google Cloud",
            "demo_mode": True,
            "report_type": "cloud_cost",
            "cost_summary": {
                "total_monthly": 42350,
                "top_services": [
                    {"service": "Compute Engine", "monthly_cost": 18200, "total_6m": 109200, "trend_6m": [16500, 17000, 17500, 18000, 18100, 18200]},
                    {"service": "Cloud SQL", "monthly_cost": 8500, "total_6m": 51000, "trend_6m": [7800, 8000, 8200, 8300, 8400, 8500]},
                    {"service": "BigQuery", "monthly_cost": 4800, "total_6m": 28800, "trend_6m": [3900, 4100, 4300, 4500, 4700, 4800]},
                    {"service": "Cloud Storage", "monthly_cost": 3200, "total_6m": 19200, "trend_6m": [2800, 2900, 3000, 3100, 3150, 3200]},
                    {"service": "GKE / Kubernetes Engine", "monthly_cost": 2800, "total_6m": 16800, "trend_6m": [2200, 2400, 2500, 2600, 2700, 2800]},
                    {"service": "Cloud Networking", "monthly_cost": 1900, "total_6m": 11400, "trend_6m": [1700, 1750, 1800, 1850, 1880, 1900]},
                    {"service": "Cloud Pub/Sub", "monthly_cost": 1200, "total_6m": 7200, "trend_6m": [1000, 1050, 1100, 1150, 1180, 1200]},
                    {"service": "Cloud Functions", "monthly_cost": 950, "total_6m": 5700, "trend_6m": [750, 800, 850, 900, 920, 950]},
                    {"service": "Cloud Memorystore", "monthly_cost": 500, "total_6m": 3000, "trend_6m": [500, 500, 500, 500, 500, 500]},
                    {"service": "Secret Manager", "monthly_cost": 300, "total_6m": 1800, "trend_6m": [250, 260, 270, 280, 290, 300]},
                ],
            },
            "compute": {
                "total_instances": 78,
                "running": 52,
                "stopped": 26,
                "machine_types": {
                    "e2-standard-4": 22,
                    "e2-standard-2": 18,
                    "n2-standard-8": 12,
                    "e2-medium": 10,
                    "n2-highmem-4": 8,
                    "c2-standard-16": 4,
                    "a2-highgpu-1g": 2,
                    "e2-micro": 2,
                },
            },
            "disk_waste": {
                "total_disks": 134,
                "unattached_disks": 31,
                "unattached_size_gb": 4800,
                "estimated_waste": 192.0,
            },
            "iam_summary": {
                "total_service_accounts": 45,
                "active_service_accounts": 38,
                "disabled_service_accounts": 7,
                "old_sa_keys": 12,
            },
            "licenses": [
                {"product_name": "Compute Engine", "total_licenses": 0, "assigned_licenses": 0, "active_users": 0, "unused_licenses": 0, "utilization_pct": 0, "monthly_cost": 18200},
                {"product_name": "Cloud SQL", "total_licenses": 0, "assigned_licenses": 0, "active_users": 0, "unused_licenses": 0, "utilization_pct": 0, "monthly_cost": 8500},
                {"product_name": "BigQuery", "total_licenses": 0, "assigned_licenses": 0, "active_users": 0, "unused_licenses": 0, "utilization_pct": 0, "monthly_cost": 4800},
            ],
            "login_activity": {
                "daily_avg_logins": 0,
                "unique_users_30d": 38,
                "total_users": 45,
            },
            "retrieved_at": datetime.utcnow().isoformat(),
        }


class AWSConnector(VendorConnector):
    """Connect to AWS APIs for cost analysis, resource utilization, and IAM user data."""

    vendor_name = "AWS"

    def __init__(self):
        self.session = None
        self.demo_mode = False

    def authenticate(self, credentials: dict) -> bool:
        import boto3

        if credentials.get("demo_mode"):
            self.demo_mode = True
            return True

        access_key = credentials.get("access_key_id", "").strip()
        secret_key = credentials.get("secret_access_key", "").strip()
        region = credentials.get("region", "us-east-1").strip()

        if not access_key or not secret_key:
            return False

        try:
            self.session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
            # Verify credentials with STS
            sts = self.session.client("sts")
            sts.get_caller_identity()
            return True
        except Exception as e:
            print(f"AWS auth failed: {e}")
            return False

    def get_license_summary(self) -> dict:
        if self.demo_mode:
            return self._get_demo_data()

        cost_data = self._get_cost_breakdown()
        ri_data = self._get_reservation_utilization()
        idle_resources = self._get_idle_resources()
        iam_data = self._get_iam_summary()

        # Build license-style entries from AWS data
        licenses = []

        # Cost by service as "licenses"
        for svc in cost_data:
            licenses.append({
                "product_name": svc["service"],
                "total_licenses": 0,
                "assigned_licenses": 0,
                "active_users": 0,
                "unused_licenses": 0,
                "utilization_pct": 0,
                "monthly_cost": svc["monthly_cost"],
                "trend_6m": svc.get("trend_6m", []),
            })

        return {
            "vendor": "AWS",
            "report_type": "cloud_cost",
            "cost_summary": {
                "total_monthly": sum(s["monthly_cost"] for s in cost_data),
                "top_services": cost_data[:10],
            },
            "reservations": ri_data,
            "idle_resources": idle_resources,
            "iam_summary": iam_data,
            "licenses": licenses[:10],
            "login_activity": {
                "daily_avg_logins": 0,
                "unique_users_30d": iam_data.get("active_users_90d", 0),
                "total_users": iam_data.get("total_users", 0),
            },
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    def _get_cost_breakdown(self) -> list:
        try:
            ce = self.session.client("ce")
            end = datetime.utcnow().replace(day=1)
            start = (end - timedelta(days=180)).replace(day=1)

            resp = ce.get_cost_and_usage(
                TimePeriod={
                    "Start": start.strftime("%Y-%m-%d"),
                    "End": end.strftime("%Y-%m-%d"),
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            service_costs = {}
            for period in resp.get("ResultsByTime", []):
                for group in period.get("Groups", []):
                    service = group["Keys"][0]
                    cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if service not in service_costs:
                        service_costs[service] = {"total": 0, "months": []}
                    service_costs[service]["total"] += cost
                    service_costs[service]["months"].append(round(cost, 2))

            num_months = max(len(resp.get("ResultsByTime", [])), 1)
            result = []
            for service, data in service_costs.items():
                if data["total"] < 1:
                    continue
                result.append({
                    "service": service,
                    "monthly_cost": round(data["total"] / num_months, 2),
                    "total_6m": round(data["total"], 2),
                    "trend_6m": data["months"],
                })

            result.sort(key=lambda x: x["monthly_cost"], reverse=True)
            return result

        except Exception as e:
            print(f"AWS Cost Explorer error: {e}")
            return []

    def _get_reservation_utilization(self) -> dict:
        try:
            ce = self.session.client("ce")
            end = datetime.utcnow()
            start = end - timedelta(days=30)

            resp = ce.get_reservation_utilization(
                TimePeriod={
                    "Start": start.strftime("%Y-%m-%d"),
                    "End": end.strftime("%Y-%m-%d"),
                },
            )

            total = resp.get("Total", {})
            util = total.get("UtilizationPercentage", "0")
            purchased = float(total.get("PurchasedHours", "0"))
            used = float(total.get("TotalActualHours", "0"))
            unused = float(total.get("UnusedHours", "0"))
            savings = float(total.get("NetRISavings", "0"))

            return {
                "utilization_pct": round(float(util), 1),
                "purchased_hours": round(purchased),
                "used_hours": round(used),
                "unused_hours": round(unused),
                "net_savings": round(savings, 2),
                "has_reservations": purchased > 0,
            }

        except Exception as e:
            print(f"AWS RI utilization error: {e}")
            return {"has_reservations": False, "utilization_pct": 0}

    def _get_idle_resources(self) -> dict:
        idle = {"ec2_stopped": 0, "ebs_unattached": 0, "eip_unassociated": 0, "estimated_waste": 0}

        try:
            ec2 = self.session.client("ec2")

            # Stopped EC2 instances
            stopped = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])
            for r in stopped.get("Reservations", []):
                idle["ec2_stopped"] += len(r.get("Instances", []))

            # Unattached EBS volumes
            volumes = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
            unattached = volumes.get("Volumes", [])
            idle["ebs_unattached"] = len(unattached)
            for vol in unattached:
                size_gb = vol.get("Size", 0)
                idle["estimated_waste"] += size_gb * 0.10  # ~$0.10/GB/month for gp3

            # Unassociated Elastic IPs
            eips = ec2.describe_addresses()
            for eip in eips.get("Addresses", []):
                if not eip.get("InstanceId") and not eip.get("NetworkInterfaceId"):
                    idle["eip_unassociated"] += 1
                    idle["estimated_waste"] += 3.65  # ~$3.65/month per unused EIP

            idle["estimated_waste"] = round(idle["estimated_waste"], 2)

        except Exception as e:
            print(f"AWS idle resources error: {e}")

        return idle

    def _get_iam_summary(self) -> dict:
        try:
            iam = self.session.client("iam")

            # Get all users
            users = []
            paginator = iam.get_paginator("list_users")
            for page in paginator.paginate():
                users.extend(page.get("Users", []))

            total_users = len(users)
            now = datetime.utcnow()
            ninety_days_ago = now - timedelta(days=90)

            active_users = 0
            inactive_users = 0
            never_logged_in = 0
            old_access_keys = 0

            for user in users:
                last_login = user.get("PasswordLastUsed")
                if last_login:
                    if last_login.replace(tzinfo=None) >= ninety_days_ago:
                        active_users += 1
                    else:
                        inactive_users += 1
                else:
                    never_logged_in += 1

                # Check for old access keys
                try:
                    keys = iam.list_access_keys(UserName=user["UserName"])
                    for key in keys.get("AccessKeyMetadata", []):
                        if key.get("Status") == "Active":
                            created = key.get("CreateDate")
                            if created and created.replace(tzinfo=None) < ninety_days_ago:
                                old_access_keys += 1
                except Exception:
                    pass

            return {
                "total_users": total_users,
                "active_users_90d": active_users,
                "inactive_users_90d": inactive_users,
                "never_logged_in": never_logged_in,
                "old_access_keys": old_access_keys,
            }

        except Exception as e:
            print(f"AWS IAM error: {e}")
            return {"total_users": 0, "active_users_90d": 0}

    def _get_demo_data(self) -> dict:
        """Realistic demo data for AWS cost and usage analysis."""
        return {
            "vendor": "AWS",
            "demo_mode": True,
            "report_type": "cloud_cost",
            "cost_summary": {
                "total_monthly": 67450,
                "top_services": [
                    {"service": "Amazon EC2", "monthly_cost": 28500, "total_6m": 171000, "trend_6m": [26000, 27200, 28000, 28500, 29100, 28500]},
                    {"service": "Amazon RDS", "monthly_cost": 12800, "total_6m": 76800, "trend_6m": [11500, 12000, 12200, 12800, 13100, 12800]},
                    {"service": "Amazon S3", "monthly_cost": 6200, "total_6m": 37200, "trend_6m": [5400, 5600, 5800, 6000, 6100, 6200]},
                    {"service": "Amazon CloudFront", "monthly_cost": 4800, "total_6m": 28800, "trend_6m": [4200, 4400, 4500, 4600, 4700, 4800]},
                    {"service": "AWS Lambda", "monthly_cost": 3900, "total_6m": 23400, "trend_6m": [3200, 3400, 3500, 3700, 3800, 3900]},
                    {"service": "Amazon ElastiCache", "monthly_cost": 3200, "total_6m": 19200, "trend_6m": [3200, 3200, 3200, 3200, 3200, 3200]},
                    {"service": "Amazon EKS", "monthly_cost": 2800, "total_6m": 16800, "trend_6m": [2200, 2400, 2500, 2600, 2700, 2800]},
                    {"service": "AWS Support (Business)", "monthly_cost": 2100, "total_6m": 12600, "trend_6m": [2100, 2100, 2100, 2100, 2100, 2100]},
                    {"service": "Amazon OpenSearch", "monthly_cost": 1850, "total_6m": 11100, "trend_6m": [1850, 1850, 1850, 1850, 1850, 1850]},
                    {"service": "Amazon DynamoDB", "monthly_cost": 1300, "total_6m": 7800, "trend_6m": [1100, 1150, 1200, 1250, 1280, 1300]},
                ],
            },
            "reservations": {
                "utilization_pct": 72.5,
                "purchased_hours": 43800,
                "used_hours": 31755,
                "unused_hours": 12045,
                "net_savings": 8200,
                "has_reservations": True,
            },
            "idle_resources": {
                "ec2_stopped": 14,
                "ebs_unattached": 47,
                "eip_unassociated": 8,
                "estimated_waste": 3420,
            },
            "iam_summary": {
                "total_users": 185,
                "active_users_90d": 142,
                "inactive_users_90d": 28,
                "never_logged_in": 15,
                "old_access_keys": 34,
            },
            "licenses": [
                {"product_name": "Amazon EC2", "total_licenses": 0, "assigned_licenses": 0, "active_users": 0, "unused_licenses": 0, "utilization_pct": 0, "monthly_cost": 28500},
                {"product_name": "Amazon RDS", "total_licenses": 0, "assigned_licenses": 0, "active_users": 0, "unused_licenses": 0, "utilization_pct": 0, "monthly_cost": 12800},
                {"product_name": "Amazon S3", "total_licenses": 0, "assigned_licenses": 0, "active_users": 0, "unused_licenses": 0, "utilization_pct": 0, "monthly_cost": 6200},
            ],
            "login_activity": {
                "daily_avg_logins": 0,
                "unique_users_30d": 142,
                "total_users": 185,
            },
            "retrieved_at": datetime.utcnow().isoformat(),
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
