from django.core.cache import cache
from datetime import datetime

CACHE_PREFIX = "paciente_revision"
CACHE_IDS_KEY = f"{CACHE_PREFIX}:all_ids"
CACHE_TIMEOUT = 86400 * 30


class RevisionService:

    @staticmethod
    def _key(paciente_id: int) -> str:
        return f"{CACHE_PREFIX}:{paciente_id}"

    @staticmethod
    def marcar_revisado(paciente_id: int, usuario_id: int, username: str):
        data = {
            "usuario_id": usuario_id,
            "username": username,
            "fecha": datetime.now().isoformat(),
        }
        cache.set(RevisionService._key(paciente_id), data, CACHE_TIMEOUT)
        ids = RevisionService.obtener_ids_revisados()
        if paciente_id not in ids:
            ids.append(paciente_id)
            cache.set(CACHE_IDS_KEY, ids, CACHE_TIMEOUT)

    @staticmethod
    def marcar_no_revisado(paciente_id: int):
        cache.delete(RevisionService._key(paciente_id))
        ids = RevisionService.obtener_ids_revisados()
        if paciente_id in ids:
            ids.remove(paciente_id)
            cache.set(CACHE_IDS_KEY, ids, CACHE_TIMEOUT)

    @staticmethod
    def esta_revisado(paciente_id: int) -> bool:
        return cache.get(RevisionService._key(paciente_id)) is not None

    @staticmethod
    def obtener_info_revision(paciente_id: int) -> dict | None:
        return cache.get(RevisionService._key(paciente_id))

    @staticmethod
    def obtener_ids_revisados() -> list:
        return cache.get(CACHE_IDS_KEY, [])

    @staticmethod
    def limpiar_todo():
        ids = RevisionService.obtener_ids_revisados()
        for pid in ids:
            cache.delete(RevisionService._key(pid))
        cache.delete(CACHE_IDS_KEY)
