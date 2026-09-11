from datetime import datetime


class ZeroEgressMonitor:

    def __init__(self):
        self.events = []

    def record_event(
        self,
        destination: str,
        bytes_sent: int,
        blocked: bool
    ):

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "destination": destination,
            "bytes_sent": bytes_sent,
            "blocked": blocked
        }

        self.events.append(event)

        return event

    def get_events(self):
        return self.events

    def get_status(self):

        total_bytes = sum(
            event["bytes_sent"]
            for event in self.events
        )

        blocked_events = sum(
            1
            for event in self.events
            if event["blocked"]
        )

        return {
            "zero_egress": total_bytes == 0,
            "total_bytes_sent": total_bytes,
            "blocked_events": blocked_events
        }