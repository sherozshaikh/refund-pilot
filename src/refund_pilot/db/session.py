from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from refund_pilot.core.config import PipelineConfig, Settings

_settings = Settings()
_pipeline = PipelineConfig()

engine = create_async_engine(
    _settings.database_url,
    pool_size=_pipeline.db_pool_size,
    max_overflow=_pipeline.db_max_overflow,
    pool_timeout=_pipeline.db_pool_timeout_seconds,
    echo=_settings.environment == "development",
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
