from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
LIBRARY_CSV_PATH = BASE_DIR / "data" / "library.csv"
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


@dataclass(frozen=True)
class LibrarySeed:
    code: str
    name: str
    district: str
    address: str
    latitude: float
    longitude: float
    homepage_url: str
    image_url: str


COORDINATE_SEEDS: dict[str, tuple[str, float, float]] = {
    "전주시립도서관꽃심": ("KKOTSIM", 35.8296, 127.1358),
    "완산도서관": ("WANSAN", 35.8068, 127.1104),
    "삼천도서관": ("SAMCHEON", 35.7885, 127.1218),
    "아중도서관": ("AJUNG", 35.8285, 127.1692),
    "평화도서관": ("PYEONGHWA", 35.7934, 127.1287),
    "금암도서관": ("GEUMAM", 35.8481, 127.1361),
    "서신도서관": ("SEOSIN", 35.8253, 127.1176),
    "쪽구름도서관": ("JJOKGUREUM", 35.8570, 127.1528),
    "송천도서관": ("SONGCHEON", 35.8617, 127.1179),
    "효자도서관": ("HYOJA", 35.8073, 127.1037),
    "건지도서관": ("GEONJI", 35.8466, 127.1473),
    "인후도서관": ("INHU", 35.8405, 127.1601),
}



def infer_district(address: str, name: str) -> str:
    if "덕진구" in address:
        return "덕진구"
    if "완산구" in address:
        return "완산구"
    if name in {"전주시립도서관꽃심", "완산도서관", "삼천도서관", "서신도서관", "평화도서관", "효자도서관"}:
        return "완산구"
    return "덕진구"



def build_fallback_seed(name: str, index: int) -> LibrarySeed:
    lat = 35.8242 + ((index % 4) - 1.5) * 0.01
    lon = 127.1480 + ((index // 4) - 1.5) * 0.01
    return LibrarySeed(
        code=f"LIB{index + 1:03d}",
        name=name,
        district="전주시",
        address="전북특별자치도 전주시",
        latitude=round(lat, 6),
        longitude=round(lon, 6),
        homepage_url="",
        image_url="",
    )



def _read_library_rows() -> list[dict[str, str]]:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            with LIBRARY_CSV_PATH.open("r", encoding=encoding, newline="") as csv_file:
                return list(csv.DictReader(csv_file))
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    return []



def load_library_seeds() -> dict[str, LibrarySeed]:
    seeds: dict[str, LibrarySeed] = {}
    if LIBRARY_CSV_PATH.exists():
        rows = _read_library_rows()
        for index, row in enumerate(rows):
            name = (row.get("도서관명") or "").strip()
            if not name:
                continue
            code, latitude, longitude = COORDINATE_SEEDS.get(name, (f"LIB{index + 1:03d}", 35.8242, 127.1480))
            address = (row.get("도서관주소") or "전북특별자치도 전주시").strip()
            homepage_url = (row.get("도서관홈페이지") or "").strip()
            image_url = (row.get("도서관이미지") or "").strip()
            seeds[name] = LibrarySeed(
                code=code,
                name=name,
                district=infer_district(address, name),
                address=address,
                latitude=latitude,
                longitude=longitude,
                homepage_url=homepage_url,
                image_url=image_url,
            )

    if seeds:
        return seeds

    fallback_names = list(COORDINATE_SEEDS.keys())
    for index, name in enumerate(fallback_names):
        code, latitude, longitude = COORDINATE_SEEDS[name]
        seeds[name] = LibrarySeed(
            code=code,
            name=name,
            district=infer_district("", name),
            address="전북특별자치도 전주시",
            latitude=latitude,
            longitude=longitude,
            homepage_url="",
            image_url="",
        )
    return seeds


LIBRARY_SEEDS = load_library_seeds()
