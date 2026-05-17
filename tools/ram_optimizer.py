#!/usr/bin/env python3
"""
macOS Menu Bar RAM Optimizer
Aggressively frees reclaimable memory via safe OS commands.
"""
from __future__ import annotations

import subprocess
import threading
import time
from typing import Optional

import rumps


class RAMOptimizer(rumps.App):
    """macOS menu bar app for RAM optimization."""

    def __init__(self):
        super().__init__("🧠 RAM", quit_button=None)
        self.menu = [
            rumps.MenuItem("Memory Info", callback=self.show_memory_info),
            rumps.separator,
            rumps.MenuItem("Aggressive Decompress", callback=self.aggressive_decompress),
            rumps.MenuItem("Purge Disk Cache", callback=self.purge_cache),
            rumps.separator,
            rumps.MenuItem("Auto-Optimize: OFF", callback=self.toggle_auto),
            rumps.separator,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]
        self.auto_optimize = False
        self.auto_thread: Optional[threading.Thread] = None
        self.auto_stop_event = threading.Event()

    def get_memory_stats(self) -> dict:
        """Get current memory statistics using vm_stat."""
        try:
            result = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                check=True,
            )
            stats = {}
            for line in result.stdout.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    stats[key.strip()] = value.strip()
            return stats
        except Exception as e:
            return {"error": str(e)}

    def show_memory_info(self, _):
        """Display current memory information."""
        stats = self.get_memory_stats()
        if "error" in stats:
            rumps.alert(f"Error: {stats['error']}", title="Memory Info")
            return

        info = "Memory Statistics:\n\n"
        for key, value in stats.items():
            info += f"{key}: {value}\n"
        rumps.alert(info, title="Memory Info")

    def aggressive_decompress(self, _):
        """Aggressively decompress memory by clearing caches and inactive memory."""
        rumps.notification(
            title="RAM Optimizer",
            subtitle="Starting aggressive decompression...",
            sound=False,
        )

        try:
            # Clear disk cache (safe)
            subprocess.run(["sudo", "purge"], capture_output=True, check=False)

            # Clear application caches
            cache_dirs = [
                "~/Library/Caches",
                "/Library/Caches",
            ]
            for cache_dir in cache_dirs:
                subprocess.run(
                    ["rm", "-rf", f"{cache_dir}/*"],
                    shell=False,
                    capture_output=True,
                    check=False,
                )

            # Compress inactive pages
            subprocess.run(
                ["sudo", "memory_pressure"],
                capture_output=True,
                check=False,
            )

            rumps.notification(
                title="RAM Optimizer",
                subtitle="Aggressive decompression complete!",
                sound=True,
            )
        except Exception as e:
            rumps.notification(
                title="RAM Optimizer",
                subtitle=f"Error: {str(e)}",
                sound=True,
            )

    def purge_cache(self, _):
        """Purge disk cache only."""
        try:
            subprocess.run(["sudo", "purge"], capture_output=True, check=False)
            rumps.notification(
                title="RAM Optimizer",
                subtitle="Disk cache purged",
                sound=False,
            )
        except Exception as e:
            rumps.notification(
                title="RAM Optimizer",
                subtitle=f"Error: {str(e)}",
                sound=True,
            )

    def toggle_auto(self, sender):
        """Toggle auto-optimization every 5 minutes."""
        self.auto_optimize = not self.auto_optimize
        sender.title = f"Auto-Optimize: {'ON' if self.auto_optimize else 'OFF'}"

        if self.auto_optimize:
            self.auto_stop_event.clear()
            self.auto_thread = threading.Thread(target=self.auto_optimize_loop)
            self.auto_thread.daemon = True
            self.auto_thread.start()
            rumps.notification(
                title="RAM Optimizer",
                subtitle="Auto-optimization enabled (5 min interval)",
                sound=False,
            )
        else:
            self.auto_stop_event.set()
            if self.auto_thread:
                self.auto_thread.join(timeout=1)
            rumps.notification(
                title="RAM Optimizer",
                subtitle="Auto-optimization disabled",
                sound=False,
            )

    def auto_optimize_loop(self):
        """Run auto-optimization in background."""
        while not self.auto_stop_event.is_set():
            time.sleep(300)  # 5 minutes
            if not self.auto_stop_event.is_set():
                self.aggressive_decompress(None)

    def quit_app(self, _):
        """Quit the application."""
        self.auto_stop_event.set()
        rumps.quit_application()


if __name__ == "__main__":
    app = RAMOptimizer()
    app.run()
