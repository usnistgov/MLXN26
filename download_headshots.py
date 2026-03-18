#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import re
import shutil
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "images"
PLACEHOLDER = IMAGES_DIR / "placeholder-person.svg"
MANIFEST = IMAGES_DIR / "headshots.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

IMG_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}

SKIP_TERMS = {
    "logo",
    "icon",
    "banner",
    "mark",
    "marke",
    "seal",
    "social",
    "share",
    "hero",
    "campus",
    "building",
    "footer",
    "header",
    "headerimage",
    "placeholder",
    "no-profile-img",
    "profile_dome",
    "waterdreampromo",
}

BOOST_TERMS = {
    "profile",
    "portrait",
    "headshot",
    "speaker",
    "staff",
    "faculty",
    "person",
    "people",
}


@dataclass
class Speaker:
    slug: str
    name: str
    profile_url: str | None
    extra_terms: tuple[str, ...] = field(default_factory=tuple)
    direct_image_url: str | None = None


SPEAKERS = [
    Speaker("volodymyr-bezguba", "Prof. Volodymyr Bezguba", "https://kau.org.ua/en/bezguba"),
    Speaker(
        "kamal-choudhary",
        "Prof. Kamal Choudhary",
        "https://engineering.jhu.edu/materials/faculty/kamal-choudhary/",
        direct_image_url="https://engineering.jhu.edu/materials/wp-content/uploads/2025/07/KC-2022-e1751919309622-980x654.jpg",
    ),
    Speaker(
        "brian-decost",
        "Dr. Brian DeCost",
        "https://www.nist.gov/people/brian-decost",
        direct_image_url="https://www.nist.gov/sites/default/files/styles/480_x_480_limit/public/images/2023/03/30/decost_photo.jpg?itok=auQscOyP",
    ),
    Speaker("changwoo-do", "Dr. Changwoo Do", "https://www.ornl.gov/staff-profile/changwoo-do"),
    Speaker(
        "alexander-hexemer",
        "Dr. Alexander Hexemer",
        "https://als.lbl.gov/people/alex-hexemer/",
        ("alex",),
        direct_image_url="https://als.lbl.gov/wp-content/uploads/2016/09/Hexemer-Headshot.png",
    ),
    Speaker(
        "david-hoogerheide",
        "Dr. David P. Hoogerheide",
        "https://www.nist.gov/people/david-p-hoogerheide",
        direct_image_url="https://www.nist.gov/sites/default/files/styles/480_x_480_limit/public/images/2019/04/25/dave_2018_0_crop2.jpg?itok=VgNbhmX0",
    ),
    Speaker(
        "jan-ilavsky",
        "Dr. Jan Ilavsky",
        "https://www.anl.gov/profile/jan-ilavsky",
        direct_image_url="https://www.anl.gov/sites/www/files/styles/profile_teaser_square_350px/public/Jan%20Ilavsky.jpg?itok=Iy5zpzVc",
    ),
    Speaker(
        "haili-jia",
        "Dr. Haili Jia",
        "https://www.anl.gov/profile/haili-jia",
        direct_image_url="https://www.anl.gov/sites/www/files/styles/profile_teaser_square_350px/public/Jia_Haili_Headshot_2.JPG?h=00546c34&itok=Xq1y_vCk",
    ),
    Speaker("aileen-luo", "Dr. Aileen Luo", None),
    Speaker("boran-ma", "Prof. Boran Ma", "https://www.maresearchlab.com/team-boranma-usm"),
    Speaker("marshall-mcdonnell", "Dr. Marshall T. McDonnell", "https://www.ornl.gov/staff-profile/marshall-t-mcdonnell"),
    Speaker("peter-mueller-buschbaum", "Prof. Dr. Peter Müller-Buschbaum", "https://www.professoren.tum.de/en/mueller-buschbaum-peter/"),
    Speaker("viktor-reshniak", "Dr. Viktor Reshniak", "https://www.ornl.gov/staff-profile/viktor-reshniak"),
    Speaker("thomas-holm-rod", "Dr. Thomas Holm Rod", "https://ess.eu/profile/thomas-holm-rod"),
    Speaker(
        "stephan-roth",
        "Prof. Dr. Stephan Volkher Roth",
        "https://photon-science.desy.de/research/research_teams/fs_sma/team/index_eng.html",
        ("svroth",),
        direct_image_url="https://photon-science.desy.de/sites/site_photonscience/content/e62/e187741/e319721/e319829/e320196/2023-10-20_Roth_Stephan-FS-SMA_MM-6358_eng.jpg",
    ),
    Speaker("jon-taylor", "Dr. Jon Taylor", "https://www.ornl.gov/content/jon-taylor"),
    Speaker("marina-tropmann-frick", "Prof. Marina Tropmann-Frick", "https://www.haw-hamburg.de/person/marina-tropmann-frick/"),
    Speaker("chi-huan-tung", "Dr. Chi-Huan Tung", "https://www.ornl.gov/staff-profile/chi-huan-tung"),
    Speaker("xiaoping-wang", "Dr. Xiaoping Wang", "https://www.ornl.gov/staff-profile/xiaoping-wang"),
    Speaker("zhongcan-xiao", "Dr. Zhongcan Xiao", "https://impact.ornl.gov/en/persons/zhongcan-xiao/"),
    Speaker(
        "bowen-zheng",
        "Dr. Bowen Zheng",
        "https://als.lbl.gov/people/bowen-zheng/",
        direct_image_url="https://als.lbl.gov/wp-content/uploads/2025/05/2025-03-24-Headshot-3I2A3944-1.jpg",
    ),
]


class ProfileParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if value}
        if tag.lower() == "meta":
            self.meta.append(attr_map)
        elif tag.lower() == "img":
            self.images.append(attr_map)


def fetch(url: str) -> tuple[bytes, dict[str, str]]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return response.read(), headers


def clean_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def speaker_terms(speaker: Speaker) -> set[str]:
    pieces = re.findall(r"[A-Za-z]+", speaker.name)
    base = {clean_term(piece) for piece in pieces if piece}
    base |= {clean_term(term) for term in speaker.extra_terms}
    return {term for term in base if term}


def choose_meta_image(page_url: str, parser: ProfileParser, speaker: Speaker) -> list[str]:
    candidates = []
    for meta in parser.meta:
        key = (meta.get("property") or meta.get("name") or "").lower()
        if key in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
            content = meta.get("content")
            if content:
                candidates.append(urljoin(page_url, content))
    return rank_candidates(page_url, candidates, speaker)


def extract_image_url(img: dict[str, str], page_url: str) -> str | None:
    for key in ("src", "data-src", "data-lazy-src", "data-original", "data-srcset", "srcset"):
        value = img.get(key)
        if not value:
            continue
        item = value.split(",")[0].strip().split(" ")[0].strip()
        if item:
            return urljoin(page_url, item)
    return None


def image_text(img: dict[str, str]) -> str:
    fields = [img.get("alt", ""), img.get("title", ""), img.get("class", ""), img.get("id", "")]
    return " ".join(fields).lower()


def rank_candidates(page_url: str, candidates: Iterable[str], speaker: Speaker) -> list[str]:
    terms = speaker_terms(speaker)
    ranked = []
    for candidate in candidates:
        text = candidate.lower()
        score = 0
        if any(term in text for term in terms):
            score += 6
        if any(term in text for term in BOOST_TERMS):
            score += 3
        if any(term in text for term in SKIP_TERMS):
            score -= 5
        if text.endswith((".jpg", ".jpeg", ".png", ".webp")):
            score += 1
        ranked.append((score, urljoin(page_url, candidate)))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in ranked]


def choose_img_tag_image(page_url: str, parser: ProfileParser, speaker: Speaker) -> list[str]:
    terms = speaker_terms(speaker)
    scored: list[tuple[int, str]] = []
    for img in parser.images:
        candidate = extract_image_url(img, page_url)
        if not candidate:
            continue
        text = image_text(img)
        score = 0
        if any(term in text for term in terms):
            score += 8
        if any(term in candidate.lower() for term in terms):
            score += 6
        if any(term in text for term in BOOST_TERMS):
            score += 3
        if any(term in text for term in SKIP_TERMS):
            score -= 5
        width = int(img.get("width", "0") or "0")
        height = int(img.get("height", "0") or "0")
        if min(width, height) >= 160:
            score += 2
        if "avatar" in text:
            score += 2
        scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored]


def choose_image_url(page_url: str, parser: ProfileParser, speaker: Speaker) -> str | None:
    seen = set()
    ordered = []
    for candidate in choose_meta_image(page_url, parser, speaker) + choose_img_tag_image(page_url, parser, speaker):
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered[0] if ordered else None


def extension_for(url: str, headers: dict[str, str]) -> str:
    content_type = headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type in IMG_EXTENSIONS:
        return IMG_EXTENSIONS[content_type]
    guessed = Path(urlparse(url).path).suffix.lower()
    if guessed in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return ".jpg" if guessed == ".jpeg" else guessed
    return ".jpg"


def write_placeholder(target: Path) -> None:
    shutil.copyfile(PLACEHOLDER, target)


def fetch_profile_image(speaker: Speaker) -> dict[str, str]:
    placeholder_name = PLACEHOLDER.name
    try:
        if speaker.direct_image_url:
            image_url = speaker.direct_image_url
        elif speaker.profile_url:
            html_bytes, _ = fetch(speaker.profile_url)
            parser = ProfileParser()
            parser.feed(html_bytes.decode("utf-8", "ignore"))
            image_url = choose_image_url(speaker.profile_url, parser, speaker)
        else:
            image_url = None
    except Exception:
        image_url = None

    if not image_url:
        return {
            "name": speaker.name,
            "slug": speaker.slug,
            "status": "placeholder",
            "profile_url": speaker.profile_url or "",
            "image": placeholder_name,
            "source_image_url": "",
        }

    try:
        image_bytes, headers = fetch(image_url)
        extension = extension_for(image_url, headers)
        filename = f"{speaker.slug}{extension}"
        target = IMAGES_DIR / filename
        target.write_bytes(image_bytes)
        return {
            "name": speaker.name,
            "slug": speaker.slug,
            "status": "downloaded",
            "profile_url": speaker.profile_url or "",
            "image": filename,
            "source_image_url": image_url,
        }
    except Exception:
        return {
            "name": speaker.name,
            "slug": speaker.slug,
            "status": "placeholder",
            "profile_url": speaker.profile_url or "",
            "image": placeholder_name,
            "source_image_url": image_url,
        }


def main() -> None:
    IMAGES_DIR.mkdir(exist_ok=True)
    manifest = [fetch_profile_image(speaker) for speaker in SPEAKERS]
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for entry in manifest:
        print(f"{entry['status']:11} {entry['slug']:26} {entry['image']}")


if __name__ == "__main__":
    main()
