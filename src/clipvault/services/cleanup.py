from clipvault.database.repository import Repository
from clipvault.utils.settings import Settings


def cleanup_history(repository: Repository, settings: Settings) -> int:
    return repository.cleanup(settings.retention_days, settings.max_history)
