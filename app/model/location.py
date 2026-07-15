from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Location(Base):
    __tablename__ = "places"

    contentid: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    region: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    contentType: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    addr1: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    addr2: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    zipcode: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    tel: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    mapx: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    mapy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    mlevel: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    firstimage: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    firstimage2: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    createdtime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    modifiedtime: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )