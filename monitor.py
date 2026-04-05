import time
import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1490304134514217040/Lxl8zePyur26s4g3CO4F0v5M7D09SF6YFxrZuLPmWU3F9vkHheASP0LwK84-Sd_-crvA"

APP_URL = "http://localhost:5001/health"
METRICS_URL = "http://localhost:5001/metrics"

CPU_THRESHOLD = 90
CHECK_INTERVAL_SECONDS = 10


def send_alert(message: str) -> None:
    try:
        requests.post(
            WEBHOOK_URL,
            json={
                "embeds": [
                    {
                        "title": "Incident Alert",
                        "description": message,
                        "color": 16711680
                    }
                ]
            },
            timeout=5,
        )
    except Exception as exc:
        print(f"Failed to send Discord alert: {exc}")


def check_service() -> None:
    try:
        response = requests.get(APP_URL, timeout=3)
        if response.status_code != 200:
            send_alert(f"ALERT: Service down. /health returned {response.status_code}")
    except Exception:
        send_alert("ALERT: Service unreachable. /health request failed.")


def check_metrics() -> None:
    try:
        response = requests.get(METRICS_URL, timeout=3)
        response.raise_for_status()
        data = response.json()

        cpu_percent = data.get("cpu_percent", 0)
        if cpu_percent > CPU_THRESHOLD:
            send_alert(f"ALERT: High CPU usage detected: {cpu_percent}%")
    except Exception:
        send_alert("ALERT: Metrics endpoint failed.")


def main() -> None:
    while True:
        check_service()
        check_metrics()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()