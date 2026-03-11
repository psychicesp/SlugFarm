import json
import socket
import sqlite3
import threading
import time
import warnings

import numpy as np
import pytest
from conftest import _BURST_STATS

from slug_farm import UDP_Slug


@pytest.fixture
def udp_auditor(tmp_path):
    db_path = tmp_path / "udp_results.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE packets (
            id INTEGER PRIMARY KEY,
            udp_id TEXT,
            payload TEXT,
            arrival_time REAL
        )
    """)
    conn.commit()
    conn.close()

    stop_event = threading.Event()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.settimeout(0.1)

    def listen():
        thread_conn = sqlite3.connect(db_path)
        while not stop_event.is_set():
            try:
                data, _ = sock.recvfrom(4096)
                decoded = json.loads(data.decode("utf-8"))
                thread_conn.execute(
                    "INSERT INTO packets (udp_id, payload, arrival_time) VALUES (?, ?, ?)",
                    (decoded.get("udp_id"), json.dumps(decoded), time.time()),
                )
                thread_conn.commit()
            except (socket.timeout, json.JSONDecodeError):
                continue
        thread_conn.close()

    listener_thread = threading.Thread(target=listen, daemon=True)
    listener_thread.start()

    yield "127.0.0.1", port, db_path

    stop_event.set()
    listener_thread.join()
    sock.close()


# --- Structural & Logic Tests (Dry Runs) ---


def test_udp_branching_and_package_integrity():
    """Verify that branching correctly updates the URL/Port and the Package target."""
    root = UDP_Slug("root", url="127.0.0.1", port=8000, slug_kwargs={"global": True})

    assert root.name == "root"
    assert root.url == "127.0.0.1"
    assert root.port == 8000

    result = root(test=True)
    package = result.output
    assert package.target == "127.0.0.1:8000"
    assert package.body["global"] is True
    assert not package.body.get("local", False)
    assert "udp_id" in package.body

    leaf = root.branch(
        branch_name="sensor",
        url_extension="v1",
        new_port=9000,
        slug_kwargs={"local": True},
    )

    assert leaf.name == "root.sensor"
    assert leaf.url == "127.0.0.1/v1"
    assert leaf.port == 9000

    result = leaf(test=True)
    package = result.output
    assert package.target == "127.0.0.1/v1:9000"
    assert package.body["global"] is True
    assert package.body["local"] is True
    assert "udp_id" in package.body


# --- Live Execution Tests (Functional) ---
def test_udp_slug_high_volume_burst(udp_auditor):
    host, port, db_path = udp_auditor

    burst_count = 100
    delay_ms = 25
    slug = UDP_Slug(
        name="telemetry",
        url=host,
        port=port,
        burst_size=burst_count,
        burst_delay_ms=delay_ms,
    )

    result = slug(command="REAP", task_kwargs={"crop": "wheat", "volume": 1000})
    assert result.ok is True

    time.sleep(1.5)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT udp_id, arrival_time FROM packets")
    rows = cursor.fetchall()
    conn.close()

    received_count = len(rows)
    success_rate = (received_count / burst_count) * 100

    print(f"UDP Success Rate: {success_rate}% ({received_count}/{burst_count})")

    assert success_rate >= 85, f"UDP Packet loss too high: {success_rate}%"

    if received_count > 0:
        first_uuid = rows[0][0]
        for row in rows:
            assert row[0] == first_uuid, "UUID changed mid-burst!"

    if received_count > 1:
        target_s = delay_ms / 1000

        arrival_times = sorted([row[1] for row in rows])

        deltas = [
            arrival_times[i] - arrival_times[i - 1]
            for i in range(1, len(arrival_times))
        ]
        avg_delta = np.mean(deltas)
        med_delta = np.median(deltas)
        std_dev = np.std(deltas)

        assert (target_s / 8) <= avg_delta <= (target_s * 8), (
            f"CRITICAL TIMING FAILURE: Average {avg_delta}s is fundamentally wrong."
        )

        soft_target_low = target_s * 0.6
        soft_target_high = target_s * 1.4
        max_allowed_std = 0.015

        is_on_target = soft_target_low <= med_delta <= soft_target_high
        is_stable = std_dev < max_allowed_std

        _BURST_STATS.append(
            {
                "name": "UDP High Volume Burst",
                "med": med_delta,
                "std": std_dev,
                "rate": success_rate,
                "ok": (0.008 <= med_delta <= 0.03) and (std_dev < 0.015),
            }
        )

        if not is_on_target or not is_stable:
            warnings.warn(
                f"\n[UDP Jitter Warning]\n"
                f"Median Delta: {med_delta:.4f}s (Target: {soft_target_low}-{soft_target_high})\n"
                f"Std Dev: {std_dev:.4f}s (Max: {max_allowed_std})\n"
                f"The burst was successful, but timing was inconsistent."
            )


def test_udp_burst_timing_logic(udp_auditor):
    host, port, db_path = udp_auditor

    burst_count = 4
    delay_ms = 200
    slug = UDP_Slug(
        name="timer_test",
        url=host,
        port=port,
        burst_size=burst_count,
        burst_delay_ms=delay_ms,
    )

    start_time = time.perf_counter()
    slug(command="timing_check")
    end_time = time.perf_counter()

    total_execution_time = end_time - start_time

    expected_delay = (burst_count - 1) * (delay_ms / 1000.0)

    assert total_execution_time >= expected_delay, (
        f"Execution too fast: {total_execution_time}s < {expected_delay}s"
    )

    assert total_execution_time < (expected_delay + 0.1), (
        f"Execution too slow: {total_execution_time}s indicates an extra sleep cycle"
    )

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT arrival_time FROM packets ORDER BY arrival_time")
    arrivals = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert len(arrivals) > 2
    gap_1 = arrivals[1] - arrivals[0]
    gap_2 = arrivals[2] - arrivals[1]

    assert 0.18 <= gap_1 <= 0.22
    assert 0.18 <= gap_2 <= 0.22
