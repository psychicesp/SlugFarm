_BURST_STATS = []


def pytest_configure(config):
    global _BURST_STATS
    _BURST_STATS = []


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """This runs at the very end of the entire test session."""
    if not _BURST_STATS:
        return

    terminalreporter.section("UDP BURST PERFORMANCE REPORT")

    # Header
    header = f"{'Test Name':<40} | {'Median':<10} | {'Std Dev':<10} | {'Success %':<10}"
    terminalreporter.write_line(header)
    terminalreporter.write_line("-" * len(header))

    for stat in _BURST_STATS:
        color = "green" if stat["ok"] else "yellow"
        line = (
            f"{stat['name']:<40} | "
            f"{stat['med']:.4f}s  | "
            f"{stat['std']:.4f}s  | "
            f"{stat['rate']:.1f}%"
        )
        terminalreporter.write_line(line, **{color: True})
