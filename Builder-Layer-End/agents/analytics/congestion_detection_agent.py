"""
Congestion Detection Agent

Reads ItemFlowObserved entities (NGSI-LD) from a JSON file, evaluates congestion
based on configurable thresholds and rules, and patches Camera entities on Stellio
only when congestion state changes (PATCH only changed attributes).

Features:
- Config-driven (YAML)
- Domain-agnostic (works with any Camera entities)
- Persistent state store to track first-breach times and history
- Batch updates to Stellio with concurrency
- Alerting on new congestion events
- Robust error handling and validation

"""

from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def now_iso() -> str:
    return datetime.utcnow().strftime(ISO_FMT)


def parse_iso(ts: str) -> datetime:
    try:
        return datetime.strptime(ts, ISO_FMT).replace(tzinfo=timezone.utc)
    except Exception:
        # Try parsing without Z
        try:
            return datetime.fromisoformat(ts).astimezone(timezone.utc)
        except Exception:
            return datetime.utcnow().replace(tzinfo=timezone.utc)


@dataclass
class CongestionConfig:
    path: str
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.load()
        self.validate()

    def load(self) -> None:
        if not Path(self.path).exists():
            raise FileNotFoundError(f"Configuration file not found: {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}
        logger.info(f"Loaded congestion config from {self.path}")

    def validate(self) -> None:
        root = self.config.get("congestion_detection")
        if root is None:
            raise ValueError("Missing 'congestion_detection' section in config")
        thresholds = root.get("thresholds")
        if not thresholds:
            raise ValueError("Missing 'thresholds' in congestion_detection config")
        for key in ("occupancy", "average_speed", "intensity"):
            if key not in thresholds:
                raise ValueError(f"Missing threshold '{key}' in config")
        stellio = root.get("stellio")
        if not stellio or "update_endpoint" not in stellio:
            raise ValueError("Missing 'stellio.update_endpoint' in config (required)")
        # base_url may be required for real HTTP calls; prefer config value
        if "base_url" not in stellio and "STELLIO_BASE_URL" not in os.environ:
            # Not raising yet; we'll accept if environment set later
            logger.warning(
                "No 'stellio.base_url' in config and STELLIO_BASE_URL is not set; HTTP calls may fail"
            )

    def get_thresholds(self) -> Dict[str, float]:
        return self.config["congestion_detection"]["thresholds"]

    def get_rules(self) -> Dict[str, Any]:
        return self.config["congestion_detection"].get("rules", {})

    def get_stellio(self) -> Dict[str, Any]:
        return self.config["congestion_detection"].get("stellio", {})

    def get_alert(self) -> Dict[str, Any]:
        return self.config["congestion_detection"].get("alert", {})

    def get_state_file(self) -> str:
        state_cfg = self.config["congestion_detection"].get("state", {})
        return state_cfg.get("file", "data/congestion_state.json")

    def get_output_config(self) -> Dict[str, Any]:
        """Return output configuration"""
        return self.config["congestion_detection"].get("output", {})


class StateStore:
    """Persistent state store for congestion statuses and history"""

    def __init__(self, path: str):
        self.path = Path(path)
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                logger.warning(f"Failed to load state file {self.path}, starting fresh")
                self.data = {}
        else:
            self.data = {}

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state to {self.path}: {e}")

    def get(self, camera_ref: str) -> Dict[str, Any]:
        default = {
            "congested": False,
            "first_breach_ts": None,
            "last_update_ts": None,
            "history": [],
        }
        return self.data.get(camera_ref, default.copy())

    def update(
        self,
        camera_ref: str,
        congested: bool,
        first_breach_ts: Optional[str],
        observed_at: Optional[str],
    ) -> None:
        state = self.data.get(
            camera_ref,
            {
                "congested": False,
                "first_breach_ts": None,
                "last_update_ts": None,
                "history": [],
            },
        )
        state["congested"] = congested
        state["first_breach_ts"] = first_breach_ts
        state["last_update_ts"] = observed_at or now_iso()
        # Append history
        state.setdefault("history", [])
        state["history"].append({"ts": state["last_update_ts"], "congested": congested})
        # Keep history length reasonable
        if len(state["history"]) > 1000:
            state["history"] = state["history"][-1000:]
        self.data[camera_ref] = state


class CongestionDetector:
    """Evaluate congestion rules for single observation"""

    def __init__(self, config: CongestionConfig, state_store: StateStore):
        self.config = config
        self.state_store = state_store
        thresholds = config.get_thresholds()
        self.occupancy_thresh = float(thresholds.get("occupancy"))
        self.avg_speed_thresh = float(thresholds.get("average_speed"))
        self.intensity_thresh = float(thresholds.get("intensity"))
        rules = config.get_rules() or {}
        self.logic = rules.get("logic", "AND").upper()
        self.min_duration = int(rules.get("min_duration", 0))

    @staticmethod
    def _get_value(entity: Dict[str, Any], prop: str) -> Optional[float]:
        # Look for property in entity; supports NGSI-LD Property structure
        try:
            prop_obj = entity.get(prop)
            if isinstance(prop_obj, dict):
                val = prop_obj.get("value")
                if val is None:
                    return None
                return float(val)
        except Exception:
            return None
        return None

    def evaluate(self, entity: Dict[str, Any]) -> Tuple[bool, bool, Optional[str], str]:
        """
        Evaluate congestion for an entity.
        Returns: (should_update, new_congested_state, reason, observedAt)
        should_update: whether congestion state changed and should be patched
        new_congested_state: boolean
        reason: textual reason (diagnostics)
        observedAt: timestamp used for observedAt
        """
        # Extract camera reference ID (Camera entity id), prefer refDevice.object
        camera_ref = self._get_camera_ref(entity)
        if not camera_ref:
            raise ValueError("Cannot determine camera reference from entity")

        occupancy = self._get_value(entity, "occupancy")
        avg_speed = self._get_value(entity, "averageSpeed")
        intensity = self._get_value(entity, "intensity")

        observed_at = None
        # Try to find observedAt from intensity/intensity property
        for prop in ("intensity", "occupancy", "averageSpeed"):
            p = entity.get(prop)
            if isinstance(p, dict):
                observed_at = p.get("observedAt")
                if observed_at:
                    break
        if not observed_at:
            observed_at = now_iso()

        # Default missing values to False in comparisons
        occ_ok = occupancy is not None and occupancy > self.occupancy_thresh
        speed_ok = avg_speed is not None and avg_speed < self.avg_speed_thresh
        int_ok = intensity is not None and intensity > self.intensity_thresh

        if self.logic == "AND":
            breached = occ_ok and speed_ok and int_ok
        else:
            breached = occ_ok or speed_ok or int_ok

        # Determine new congested state considering min_duration and previous state
        prev_state = self.state_store.get(camera_ref)
        prev_congested = bool(prev_state.get("congested", False))
        first_breach_ts = prev_state.get("first_breach_ts")

        reason = (
            f"occ={occupancy}, speed={avg_speed}, int={intensity}, logic={self.logic}"
        )

        if breached:
            if prev_congested:
                # Already congested, no change
                return (False, True, reason, observed_at)
            # Not currently congested: check min_duration
            if first_breach_ts is None:
                # Start timer (or immediate if min_duration is 0)
                if self.min_duration == 0:
                    # Immediate congestion
                    return (True, True, reason + "; immediate", observed_at)
                first_breach_ts = observed_at
                # Not yet enough duration
                return (False, False, reason + "; started_timer", observed_at)
            else:
                # Calculate elapsed
                elapsed = (
                    parse_iso(observed_at) - parse_iso(first_breach_ts)
                ).total_seconds()
                if elapsed >= self.min_duration:
                    # Now considered congested
                    return (True, True, reason + f"; elapsed={elapsed}", observed_at)
                else:
                    return (False, False, reason + f"; elapsed={elapsed}", observed_at)
        else:
            # Reset timer if it exists and clear congestion state
            if prev_congested:
                # Was congested before, now cleared -> update required
                return (True, False, reason + "; cleared", observed_at)
            if first_breach_ts is not None:
                # Timer existed but breach cleared before min_duration
                return (False, False, reason + "; timer_reset", observed_at)
            return (False, False, reason + "; no_breach", observed_at)

    def _get_camera_ref(self, entity: Dict[str, Any]) -> Optional[str]:
        # Prefer refDevice.object
        rd = entity.get("refDevice")
        if isinstance(rd, dict) and rd.get("object"):
            return rd.get("object")
        # Otherwise, attempt to parse from id (ItemFlowObserved:...)
        eid = entity.get("id")
        if isinstance(eid, str):
            # If id contains camera id after last ':' maybe can't map to camera ref
            # Fallback: return entity id (some deployments may use same id)
            return eid
        return None


class CongestionDetectionAgent:
    """Main agent class for congestion detection"""

    def __init__(self, config_path: str = "config/congestion_config.yaml") -> None:
        self.config = CongestionConfig(config_path)
        state_file = self.config.get_state_file()
        self.state_store = StateStore(state_file)
        self.detector = CongestionDetector(self.config, self.state_store)
        stellio = self.config.get_stellio()
        self.stellio_base = stellio.get("base_url") or os.environ.get(
            "STELLIO_BASE_URL"
        )
        self.update_endpoint = stellio.get("update_endpoint")
        self.batch_updates = bool(stellio.get("batch_updates", True))
        self.max_workers = int(stellio.get("max_workers", 4))
        self.alert_cfg = self.config.get_alert()
        self.session = requests.Session()

        if not self.update_endpoint:
            raise ValueError("Stellio update_endpoint is required in config")
        if not self.stellio_base:
            logger.warning("Stellio base URL not configured; HTTP calls may fail")

    def _build_patch_payload(self, congested: bool, observed_at: str) -> Dict[str, Any]:
        return {
            "congested": {
                "type": "Property",
                "value": bool(congested),
                "observedAt": observed_at,
            }
        }

    def _patch_entity(
        self, entity_id: str, payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Send PATCH to Stellio for entity attributes update."""
        url = None
        try:
            # Build full URL
            if self.stellio_base:
                url = self.stellio_base.rstrip("/") + self.update_endpoint.format(
                    id=entity_id
                )
            else:
                url = self.update_endpoint.format(id=entity_id)
            headers = {"Content-Type": "application/ld+json"}
            logger.debug(f"PATCH {url} payload={payload}")
            resp = self.session.patch(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            return True, resp.status_code, None
        except Exception as e:
            logger.error(f"Failed to PATCH {url}: {e}")
            return (
                False,
                (
                    getattr(e, "response", None).status_code
                    if hasattr(e, "response") and e.response is not None
                    else None
                ),
                str(e),
            )

    def _alert(self, camera_ref: str, entity: Dict[str, Any], observed_at: str) -> None:
        if not self.alert_cfg.get("enabled", False):
            return
        # Very basic alert: append to local alerts file
        alerts_file = Path("data/alerts.json")
        alert = {
            "camera": camera_ref,
            "observedAt": observed_at,
            "message": f"Congestion detected for {camera_ref} at {observed_at}",
        }
        try:
            alerts_file.parent.mkdir(parents=True, exist_ok=True)
            if alerts_file.exists():
                with open(alerts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
            data.append(alert)
            with open(alerts_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Alert generated for {camera_ref}")
        except Exception as e:
            logger.error(f"Failed to write alert for {camera_ref}: {e}")

    def process_observations_file(self, input_file: str) -> List[Dict[str, Any]]:
        """
        Process observations JSON file and update Stellio when congestion state changes.
        Returns list of result dicts with camera_ref, updated(bool), success(bool), status_code, error
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Observations file not found: {input_file}")

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            # Support both list and object with key 'observations' or 'entities'
            if "observations" in data:
                entities = data["observations"]
            elif "entities" in data:
                entities = data["entities"]
            else:
                # Assume it's a single entity or keyed object
                # try to flatten
                entities = data.get("data") or data.get("cameras") or []
        elif isinstance(data, list):
            entities = data
        else:
            entities = []

        results: List[Dict[str, Any]] = []
        to_update: List[Tuple[str, Dict[str, Any], Dict[str, Any], bool]] = (
            []
        )  # (camera_ref,payload,entity,new_state)

        for entity in entities:
            try:
                should_update, new_state, reason, observed_at = self.detector.evaluate(
                    entity
                )
            except Exception as e:
                logger.error(f"Skipping entity due to evaluation error: {e}")
                continue
            camera_ref = self.detector._get_camera_ref(entity)
            prev_state = self.state_store.get(camera_ref)

            # If a first_breach_ts should be initialized or reset based on reasons
            if "started_timer" in (reason or ""):
                # initialize timer
                self.state_store.update(camera_ref, False, observed_at, observed_at)
                results.append(
                    {
                        "camera": camera_ref,
                        "updated": False,
                        "success": True,
                        "reason": reason,
                    }
                )
                continue

            if should_update:
                # Build payload and schedule update
                payload = self._build_patch_payload(new_state, observed_at)
                to_update.append((camera_ref, payload, entity, new_state))
            else:
                # If no update needed, we may still need to update first_breach_ts or reset it
                # Detector logic handles timer resets and returns no update; update state accordingly
                # Update state store based on detector outputs
                # If detector returned "timer_reset" or "no_breach" it implies first_breach_ts should be None
                if (
                    "timer_reset" in (reason or "")
                    or "no_breach" in (reason or "")
                    or "cleared" in (reason or "")
                ):
                    # Reset timer and set congested False
                    self.state_store.update(camera_ref, False, None, observed_at)
                results.append(
                    {
                        "camera": camera_ref,
                        "updated": False,
                        "success": True,
                        "reason": reason,
                    }
                )

        # Execute updates (batch or sequential)
        update_results: List[Dict[str, Any]] = []
        if to_update:
            if self.batch_updates:
                # Use ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=self.max_workers) as exe:
                    futures = {
                        exe.submit(self._patch_entity, cam, payload): (
                            cam,
                            payload,
                            ent,
                            new_st,
                        )
                        for cam, payload, ent, new_st in to_update
                    }
                    for fut in as_completed(futures):
                        cam, payload, ent, new_st = futures[fut]
                        try:
                            success, status_code, error = fut.result()
                        except Exception as e:
                            success = False
                            status_code = None
                            error = str(e)
                        update_results.append(
                            {
                                "camera": cam,
                                "updated": True,
                                "success": success,
                                "status_code": status_code,
                                "error": error,
                            }
                        )
                        if success:
                            # Update state store with new_st (True or False)
                            prev = self.state_store.get(cam)
                            if new_st:
                                # Set congested True
                                fb = prev.get("first_breach_ts") or now_iso()
                                self.state_store.update(
                                    cam,
                                    True,
                                    fb,
                                    payload.get("congested", {}).get("observedAt"),
                                )
                            else:
                                # Clear congestion
                                self.state_store.update(
                                    cam,
                                    False,
                                    None,
                                    payload.get("congested", {}).get("observedAt"),
                                )
                            # Alert if notify_on_change and previous was False
                            if self.alert_cfg.get(
                                "enabled", False
                            ) and self.alert_cfg.get("notify_on_change", False):
                                if not prev.get("congested", False) and new_st:
                                    self._alert(
                                        cam,
                                        ent,
                                        payload.get("congested", {}).get("observedAt"),
                                    )
                        else:
                            logger.error(f"Failed to update {cam}: {error}")
            else:
                # Sequential updates
                for cam, payload, ent, new_st in to_update:
                    success, status_code, error = self._patch_entity(cam, payload)
                    update_results.append(
                        {
                            "camera": cam,
                            "updated": True,
                            "success": success,
                            "status_code": status_code,
                            "error": error,
                        }
                    )
                    if success:
                        prev = self.state_store.get(cam)
                        if new_st:
                            # Set congested True
                            fb = prev.get("first_breach_ts") or now_iso()
                            self.state_store.update(
                                cam,
                                True,
                                fb,
                                payload.get("congested", {}).get("observedAt"),
                            )
                        else:
                            # Clear congestion
                            self.state_store.update(
                                cam,
                                False,
                                None,
                                payload.get("congested", {}).get("observedAt"),
                            )
                        if self.alert_cfg.get("enabled", False) and self.alert_cfg.get(
                            "notify_on_change", False
                        ):
                            if not prev.get("congested", False) and new_st:
                                self._alert(
                                    cam,
                                    ent,
                                    payload.get("congested", {}).get("observedAt"),
                                )
                    else:
                        logger.error(f"Failed to update {cam}: {error}")

        # Combine results
        results.extend(update_results)
        # Save state
        self.state_store.save()

        # ============================================================
        # CRITICAL FIX: Write congestion.json output file
        # ============================================================
        # This ensures downstream monitoring and analytics have structured data
        output_config = self.config.get_output_config()
        congestion_file = output_config.get("congestion_file", "data/congestion.json")

        # Build congestion events list (even if empty)
        congestion_events = []
        for res in results:
            if res.get("updated") and res.get("success"):
                # Extract congestion event data
                congestion_event = {
                    "camera": res.get("camera"),
                    "updated": True,
                    "congested": True,  # Only successful updates are congestion=true
                    "success": True,
                    "timestamp": now_iso(),
                }
                congestion_events.append(congestion_event)

        # ALWAYS write file (even if empty list) for consistency
        try:
            congestion_path = Path(congestion_file)
            congestion_path.parent.mkdir(parents=True, exist_ok=True)

            with open(congestion_file, "w", encoding="utf-8") as f:
                json.dump(congestion_events, f, indent=2, ensure_ascii=False)

            logger.info(
                f"✅ Saved {len(congestion_events)} congestion events to {congestion_file}"
            )
        except Exception as e:
            logger.error(f"Failed to write congestion file {congestion_file}: {e}")
        return results


def main(config: Optional[Dict[str, Any]] = None):
    """Main entry point

    Args:
        config: Optional workflow agent config (from orchestrator)
    """
    import argparse

    # Use config from orchestrator if provided
    if config:
        input_file = config.get("input_file", "data/observations.json")
        config_path = config.get("config_path", "config/congestion_config.yaml")
    else:
        parser = argparse.ArgumentParser(description="Congestion Detection Agent")
        parser.add_argument(
            "input_file",
            nargs="?",
            default="data/observations.json",
            help="Observations JSON file",
        )
        parser.add_argument(
            "--config",
            default="config/congestion_config.yaml",
            help="Path to congestion config",
        )
        args = parser.parse_args()
        input_file = args.input_file
        config_path = args.config

    agent = CongestionDetectionAgent(config_path)
    res = agent.process_observations_file(input_file)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
