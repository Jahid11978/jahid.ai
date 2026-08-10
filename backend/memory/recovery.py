from enum import StrEnum


class RecoveryStage(StrEnum):
    DETECT = "detect"
    CLASSIFY = "classify"
    PROTECT = "protect_current_state"
    RESTORE_SERVICE = "restore_service"
    RESTORE_DATABASE = "restore_database"
    RESTORE_MEMORY_INDEX = "restore_memory_indexes"
    VERIFY = "verify"
    RESUME = "resume"


class RecoveryPlan:
    ORDER = tuple(RecoveryStage)

    def __iter__(self):
        return iter(self.ORDER)
