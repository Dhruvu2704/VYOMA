from services.zero_egress import ZeroEgressMonitor


monitor = ZeroEgressMonitor()


result = monitor.check_connection(
    "example.com",
    443
)


print(result)