# Относительный импорт из подпапки providers
from .providers.bucket_loader import (
    get_bucket_loader_repo,
    get_bucket_loader_service,
)


from .providers.machine_learning import (
    get_embedding_service,
    get_ml_service,
)


from .providers.minio import (
    get_minio_client,
)


from .providers.photoscan import (
    get_photoscan_repo,
    get_photoscan_service,
)


from .providers.units import (
    get_units_repo,
    get_units_service,
)


from .providers.prisoners import (
    get_prisoner_repo,
    get_prisoner_service,
)


from .providers.schedule import (
    get_schedule_repo,
    get_schedule_service,
)


__all__ = [
    # Units
    "get_units_repo",
    "get_units_service",
    # MinIO
    "get_minio_client",
    # Machine Learning
    "get_ml_service",
    "get_embedding_service",
    # Bucket Loader
    "get_bucket_loader_repo",
    "get_bucket_loader_service",
    # PhotoScan
    "get_photoscan_repo",
    "get_photoscan_service",
    # Prisoners
    "get_prisoner_repo",
    "get_prisoner_service",
    # Schedule
    "get_schedule_repo",
    "get_schedule_service",
]