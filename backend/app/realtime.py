"""In-process WebSocket hub. For several server processes, back this with Redis pub/sub."""
import logging
from collections import defaultdict

import anyio


class Hub:
    def __init__(self):
        self.conns: dict = defaultdict(list)

    def add(self, clinic_id, user_id, role, ws):
        self.conns[clinic_id].append((user_id, role, ws))

    def remove(self, clinic_id, ws):
        self.conns[clinic_id] = [c for c in self.conns[clinic_id] if c[2] is not ws]

    def count(self):
        return sum(len(v) for v in self.conns.values())

    async def broadcast(self, clinic_id, event, user_ids=None, roles=None):
        for uid, role, ws in list(self.conns.get(clinic_id, [])):
            if (user_ids is not None and uid not in user_ids) or (roles is not None and role not in roles):
                continue
            try:
                await ws.send_json(event)
            except Exception:
                self.remove(clinic_id, ws)


hub = Hub()


def publish(clinic_id, event: dict, user_ids=None, roles=None):
    """Call from sync endpoints after the DB commit. Never raises."""
    from fastapi.encoders import jsonable_encoder

    try:
        anyio.from_thread.run(hub.broadcast, clinic_id, jsonable_encoder(event), set(user_ids) if user_ids is not None else None, tuple(roles) if roles else None)
    except Exception:
        logging.getLogger("clinicos.realtime").debug("publish skipped (no event loop)", exc_info=True)
