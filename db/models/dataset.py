from sqlalchemy import Integer, String, Text, Boolean, JSON, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32))  # internal/api/file
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    access_level: Mapped[str] = mapped_column(String(16), default="free")  # free/premium/enterprise
    added_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
