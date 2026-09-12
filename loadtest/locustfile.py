import os

from locust import HttpUser, between, task


class HotelStaffUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self):
        token = os.getenv("LOAD_TEST_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("LOAD_TEST_ACCESS_TOKEN is required")
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)
    def summary(self):
        self.client.get("/api/dashboard/summary", name="dashboard-summary")

    @task(3)
    def requests(self):
        self.client.get("/api/dashboard/requests?limit=50", name="dashboard-requests")

    @task(2)
    def guests(self):
        self.client.get("/api/dashboard/guests?limit=50", name="dashboard-guests")

    @task(1)
    def analytics(self):
        self.client.get("/api/dashboard/analytics", name="dashboard-analytics")
