import requests
import time
import re
import json
import sys
import html as html_lib
from datetime import datetime
from urllib.parse import unquote, urljoin


JAPAN_LAT_RANGE = (20.0, 46.5)
JAPAN_LNG_RANGE = (122.0, 154.5)


def normalize_japan_coords(lat, lng):
    """日本国内らしい緯度経度なら8桁固定の文字列で返す"""
    try:
        lat_num = float(lat)
        lng_num = float(lng)
    except (TypeError, ValueError):
        return None

    if (JAPAN_LAT_RANGE[0] <= lat_num <= JAPAN_LAT_RANGE[1] and
            JAPAN_LNG_RANGE[0] <= lng_num <= JAPAN_LNG_RANGE[1]):
        return f"{lat_num:.8f}", f"{lng_num:.8f}"
    return None


def extract_prefecture(address):
    """住所から都道府県を抽出する"""
    pref_list = [
        "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
        "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
        "岐阜県", "静岡県", "愛知県", "三重県",
        "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
        "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県",
        "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
    ]
    for pref in pref_list:
        if address.startswith(pref):
            return pref
    return None


def parse_rsc_data_chunk(html):
    """RSCペイロード（Next.js React Server Components）からdataChunkを抽出する"""
    pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)
    for p in pushes:
        if 'dataChunk' not in p:
            continue
        unescaped = p.replace('\\"', '"').replace('\\n', '\n')
        chunk_match = re.search(r'"dataChunk":\[(.*?)\],"total', unescaped, re.DOTALL)
        if chunk_match:
            try:
                return json.loads('[' + chunk_match.group(1) + ']')
            except json.JSONDecodeError:
                pass
    return []


def extract_direct_query_coords(text):
    """Google Maps URLの query=LAT,LNG 形式から座標を抽出する"""
    decoded = unquote(html_lib.unescape(text))
    for lat, lng in re.findall(
            r'query=([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)',
            decoded):
        coords = normalize_japan_coords(lat, lng)
        if coords:
            return coords
    return None


def extract_google_maps_url(page_html):
    """詳細ページにあるGoogle Mapsリンクを抽出する"""
    for href in re.findall(r'href="(https://www\.google\.com/maps/[^"]+)"',
                           page_html):
        return html_lib.unescape(href)
    return None


def extract_google_preview_url(google_html, base_url):
    """Google Maps検索結果からpreview endpointのURLを抽出する"""
    match = re.search(r'<link href="([^"]*?/maps/preview/place[^"]+)"',
                      google_html)
    if not match:
        return None
    return urljoin(base_url, html_lib.unescape(match.group(1)))


def extract_coords_from_google_preview(preview_text):
    """Google Maps previewレスポンスから日本国内の座標を抽出する"""
    patterns = [
        # preview内の店舗データ: [null,null,LAT,LNG]
        r'\[null,null,([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)\]',
        # Google Mapsの共有URL断片: /@LAT,LNG,ZOOM
        r'/@([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?),',
        # dataパラメータ: !3dLAT!4dLNG
        r'!3d([+-]?\d+(?:\.\d+)?)!4d([+-]?\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        for lat, lng in re.findall(pattern, preview_text):
            coords = normalize_japan_coords(lat, lng)
            if coords:
                return coords
    return None


def get_coords_from_google_maps(maps_url, headers):
    """Place ID形式のGoogle Mapsリンクから座標を取得する"""
    try:
        search_res = requests.get(maps_url, headers=headers, timeout=15)
        search_res.raise_for_status()

        preview_url = extract_google_preview_url(search_res.text,
                                                 search_res.url)
        if not preview_url:
            return None

        preview_headers = dict(headers)
        preview_headers["Referer"] = maps_url
        preview_res = requests.get(preview_url, headers=preview_headers,
                                   timeout=15)
        preview_res.raise_for_status()
        return extract_coords_from_google_preview(preview_res.text)
    except Exception as e:
        print(f"    google maps error: {type(e).__name__}: {e}")
    return None


def get_coords_from_detail(slug, headers):
    """店舗詳細ページからGoogle Maps URLの緯度経度を取得する"""
    url = f"https://www.gigo.co.jp/shops/{slug}"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        # 旧形式のGoogle Maps URL: query=LAT,LNG
        coords = extract_direct_query_coords(res.text)
        if coords:
            return coords

        # 新形式のGoogle Maps URL: query=NAME&query_place_id=...
        maps_url = extract_google_maps_url(res.text)
        if maps_url:
            return get_coords_from_google_maps(maps_url, headers)
    except Exception as e:
        print(f"    detail page error ({slug}): {type(e).__name__}: {e}")
    return None


def scrape_gigo_shops():
    """GiGO店舗情報を新サイト (www.gigo.co.jp) からスクレイピングする

    新サイトはNext.js (React Server Components) で構築されており、
    一覧ページのRSCペイロードから店舗名・住所を、
    詳細ページのGoogle Maps URLから緯度経度を取得する。
    """
    start_time = datetime.now()
    print("GiGO shop scraping started")
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
    }
    base_url = "https://www.gigo.co.jp/shops"

    # ステップ1: 全ページから店舗一覧を取得
    print("\n[Step 1] Fetching shop list from all pages...")
    all_shops = []
    page = 1

    while True:
        url = f"{base_url}?brand=001&q=&page={page}&_rsc=jr41v"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
        except Exception as e:
            print(f"  Page {page} error: {e}")
            break

        shops = parse_rsc_data_chunk(res.text)

        if not shops:
            print(f"  Page {page}: empty -> done")
            break

        all_shops.extend(shops)
        print(f"  Page {page}: {len(shops)} shops (total: {len(all_shops)})")
        page += 1
        time.sleep(0.5)

    total_shops = len(all_shops)
    print(f"\nShop list complete: {total_shops} shops found")
    print("=" * 60)

    # ステップ2: 各店舗の詳細ページから座標を取得
    est_minutes = total_shops * 1.2 / 60
    print(f"\n[Step 2] Fetching coordinates from detail pages...")
    print(f"  (~{total_shops} shops x 1.2s = ~{est_minutes:.1f} min)\n")

    values = [[
        "タイムスタンプ", "カテゴリ", "画像", "緯度", "経度",
        "スポット名", "紹介文", "Instagram", "Twitter", "公式サイト", "Facebook"
    ]]

    success_count = 0
    skipped_no_coords = 0
    skipped_no_pref = 0
    skipped_overseas = 0
    skipped_closed = 0

    for idx, shop in enumerate(all_shops, 1):
        name = shop.get("name", "")
        slug = shop.get("slug", "")
        address = shop.get("address", "")
        detail_url = f"https://www.gigo.co.jp/shops/{slug}"

        # 閉店・閉鎖・closed 店舗をスキップ
        if re.search(r'閉店|閉鎖|closed', name, re.IGNORECASE):
            print(f"  [{idx}/{total_shops}] CLOSED skip: {name}")
            skipped_closed += 1
            continue

        # 都道府県を住所から判定
        pref = extract_prefecture(address)

        if not pref:
            # 海外店舗チェック（日本語が含まれていないか判定）
            has_japanese = bool(re.search(
                r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', address
            ))
            if not has_japanese:
                print(f"  [{idx}/{total_shops}] OVERSEAS skip: {name}")
                skipped_overseas += 1
                continue
            else:
                print(f"  [{idx}/{total_shops}] NO_PREF skip: "
                      f"{name} ({address[:30]}...)")
                skipped_no_pref += 1
                continue

        # 詳細ページから座標取得
        print(f"  [{idx}/{total_shops}] {name} ...", end="", flush=True)
        time.sleep(1.2)

        coords = get_coords_from_detail(slug, headers)
        if coords:
            lat, lng = coords
            print(f" OK ({lat}, {lng})")
        else:
            print(" NO_COORDS")
            skipped_no_coords += 1
            continue

        # データ追加（旧プログラムと同じフォーマット）
        values.append([
            "",                    # タイムスタンプ
            pref,                  # カテゴリ（都道府県）
            "",                    # 画像
            lat,                   # 緯度
            lng,                   # 経度
            name,                  # スポット名
            address,               # 紹介文（住所）
            "",                    # Instagram
            f"https://twitter.com/intent/tweet?text={name}%20{address}",
            detail_url,            # 公式サイト
            ""                     # Facebook
        ])
        success_count += 1

    # ステップ3: 結果をJSON保存
    end_time = datetime.now()
    duration = end_time - start_time
    duration_str = str(duration).split('.')[0]

    result = {
        "range": "スポットデータ",
        "majorDimension": "ROWS",
        "values": values
    }

    filename = "data.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"\nJSON save error: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)
    print(f"Output: {filename}")
    print(f"Success: {success_count}")
    print(f"  Closed:   {skipped_closed}")
    print(f"  No coord: {skipped_no_coords}")
    print(f"  No pref:  {skipped_no_pref}")
    print(f"  Overseas: {skipped_overseas}")
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration_str}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    scrape_gigo_shops()
