from __future__ import annotations

class MultimodalGrounder:
    """Bridges vocal references with coordinate gesture maps to resolve deictic targets."""
    def resolve_deictic_references(self, verbal_command: str, gaze_quadrant: int) -> str:
        normalized = verbal_command.lower()
        deictic_markers = ["open this", "run that", "inspect this", "what is this"]
        
        has_deictic = any(marker in normalized for marker in deictic_markers)
        if not has_deictic:
            return verbal_command

        # Coordinates quadrants maps to specific system targets
        quadrant_assets = {
            1: "primary_dashboard_log.txt",
            2: "camera_node_feed_1.bin",
            3: "sensor_telemetry_out.csv",
            4: "system_security_manifest.json"
        }
        
        target_asset = quadrant_assets.get(gaze_quadrant, "active_workspace_view")
        return f"{verbal_command} (resolved target: {target_asset})"
