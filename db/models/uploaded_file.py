"""
UploadedFile — файлы загруженные пользователями для поиска (CSV, JSON, TXT).
"""
from sqlalchemy import BigInteger, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class UploadedFile(Base, TimestampMixin):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(256))
    file_path: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(16))   # csv / json / txt
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    columns_info: Mapped[str | None] = mapped_column(Text, nullable=True)
