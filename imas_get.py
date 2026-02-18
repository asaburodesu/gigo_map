# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json
import time

# シングルクォートをダブルクォートに変換し、JSONを修正する関数
def fix_json_string(json_str):
    try:
        json_str = re.sub(r'\b(\w+):(?=\s*["[\d{])', r'"\1":', json_str)
        def escape_special_chars(match):
            value = match.group(1)
            value = (value.replace('"', '\\"')
                         .replace('&', '\\&')
                         .replace('\n', '\\n')
                         .replace('\r', '\\r')
                         .replace('\t', '\\t'))
            return f'"{value}"'
        json_str = re.sub(r":\s*'([^']*)'", escape_special_chars, json_str)
        json_str = re.sub(r"\[\s*'([^']*)'\s*]", r'["\1"]', json_str)
        json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        return json_str
    except Exception as e:
        print(f"JSON文字列修正エラー: {e}")
        return json_str

# 詳細ページから緯度・経度を取得する関数
def get_lat_lng_from_detail_page(detail_url):
    try:
        res = requests.get(detail_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        script_tags = soup.find_all("script")
        for script in script_tags:
            # Google MapsのURLから緯度・経度を抽出
            src_match = re.search(r"var src = 'https://www\.google\.com/maps/embed/v1/place\?&q=([\d.-]+),([\d.-]+)'", script.text)
            if src_match:
                latitude = src_match.group(1)
                longitude = src_match.group(2)
                print(f"詳細ページから取得 - 緯度: {latitude}, 経度: {longitude} ({detail_url})")
                return latitude, longitude
            # フォールバック: routeSearchボタンから取得
            button = soup.find("button", id="routesearch_btn")
            if button and "routeSearch" in button.get("onclick", ""):
                coord_match = re.search(r"routeSearch\(([\d.-]+),\s*([\d.-]+)\)", button["onclick"])
                if coord_match:
                    latitude = coord_match.group(1)
                    longitude = coord_match.group(2)
                    print(f"routeSearchから取得 - 緯度: {latitude}, 経度: {longitude} ({detail_url})")
                    return latitude, longitude
        print(f"警告: 詳細ページ {detail_url} でGoogle Maps URLまたはrouteSearchが見つかりませんでした")
        return "", ""
    except requests.RequestException as e:
        print(f"詳細ページ取得エラー ({detail_url}): {e}")
        return "", ""
    except Exception as e:
        print(f"詳細ページその他のエラー ({detail_url}): {e}")
        return "", ""

# 出力ファイルを開く
with open('data.json', 'w', encoding='utf-8', errors='ignore') as f:
    base_json_dict = {
        "range": "スポットデータ",
        "majorDimension": "ROWS",
        "values": [
            ["タイムスタンプ", "カテゴリ", "画像", "緯度", "経度", "スポット名", "紹介文", "Instagram", "Twitter", "公式サイト", "Facebook"]
        ]
    }

    for area_code in range(1, 48):
        url = f'https://bandainamco-am.co.jp/am/vg/idolmaster-tours/location/list?area=JP-{str(area_code).zfill(2)}'
        print(f"スクレイピング中: {url}")
        
        try:
            res = requests.get(url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            prefecture = soup.find("h1").text.strip() if soup.find("h1") else "不明"
            dl_elements = soup.find_all("dl")
            spot_dict = {}
            for dl in dl_elements:
                dt_elements = dl.find_all("dt")
                dd_elements = dl.find_all("dd")
                i = 0
                while i < len(dd_elements):
                    if dd_elements[i].get("class") == ["address"]:
                        name = dt_elements[i // 2].text.strip()
                        address = dd_elements[i].text.strip()
                        count = dd_elements[i + 1].text.strip() if i + 1 < len(dd_elements) and dd_elements[i + 1].get("class") == ["count"] else ""
                        detail_url = dt_elements[i // 2].find("a")["href"] if dt_elements[i // 2].find("a") else ""
                        if detail_url.startswith("./detail"):
                            detail_url = f"https://bandainamco-am.co.jp/am/vg/idolmaster-tours/location{detail_url[1:]}"
                        spot_dict[name] = {
                            "address": address,
                            "count": count,
                            "detail_url": detail_url,
                            "latitude": "",
                            "longitude": ""
                        }
                        i += 2
                    else:
                        i += 1

            # JavaScript内のlocations配列から緯度・経度を取得
            script_tags = soup.find_all("script")
            locations_found = False
            for script in script_tags:
                if "var locations =" in script.text:
                    locations_text = re.search(r'var locations = (\[.*?\]);', script.text, re.DOTALL)
                    if locations_text:
                        locations_found = True
                        try:
                            raw_json = locations_text.group(1)
                            print(f"抽出されたlocations: {raw_json[:100]}...")
                            fixed_json = fix_json_string(raw_json)
                            print(f"修正後のJSON: {fixed_json[:100]}...")
                            locations_data = json.loads(fixed_json)
                            # スポットごとにlocationsをチェック
                            for name in spot_dict:
                                found = False
                                for location in locations_data:
                                    loc_name = location.get("name", "").strip()
                                    if loc_name == name:
                                        spot_dict[name]["latitude"] = str(location.get("latitude", ""))
                                        spot_dict[name]["longitude"] = str(location.get("longitude", ""))
                                        print(f"スポット: {name}, 緯度: {spot_dict[name]['latitude']}, 経度: {spot_dict[name]['longitude']} (from locations)")
                                        found = True
                                        break
                                if not found and spot_dict[name]["detail_url"]:
                                    print(f"スポット {name} はlocationsにないため、詳細ページをチェック: {spot_dict[name]['detail_url']}")
                                    latitude, longitude = get_lat_lng_from_detail_page(spot_dict[name]["detail_url"])
                                    spot_dict[name]["latitude"] = latitude
                                    spot_dict[name]["longitude"] = longitude
                                    time.sleep(1)  # 詳細ページリクエストの間隔
                        except json.JSONDecodeError as e:
                            print(f"JSONパースエラー ({url}): {e}")
                            print(f"問題のJSON文字列: {fixed_json}...")
                            continue
                        except Exception as e:
                            print(f"その他のエラー ({url}): {e}")
                            continue

            if not locations_found:
                print(f"警告: locations配列が見つかりませんでした ({url})。全スポットの詳細ページから取得を試みます。")
                for name, info in spot_dict.items():
                    if info["detail_url"]:
                        print(f"詳細ページをスクレイピング中: {info['detail_url']}")
                        latitude, longitude = get_lat_lng_from_detail_page(info["detail_url"])
                        spot_dict[name]["latitude"] = latitude
                        spot_dict[name]["longitude"] = longitude
                        time.sleep(1)

            # JSONデータに追加（緯度・経度が空でないスポットのみ）
            for name, info in spot_dict.items():
                # 変更点1: 緯度・経度が空の場合、スポットをスキップ
                if not info["latitude"] or not info["longitude"]:
                    print(f"スポット {name} は緯度・経度が見つからないため除外します")
                    continue
                # 変更点2: Twitter URLをhttps://twitter.com/intent/tweet?text=<住所><店舗名>に変更、URLエンコードなし
                twitter_url = f"https://twitter.com/intent/tweet?text={info['address']}{name}"
                value = [
                    "",
                    prefecture,
                    "",
                    info["latitude"],
                    info["longitude"],
                    name,
                    f"{info['address']}\n{info['count']}",
                    "",
                    twitter_url,
                    info["detail_url"],
                    ""
                ]
                base_json_dict["values"].append(value)

        except requests.RequestException as e:
            print(f"ページ取得エラー ({url}): {e}")
            continue

        time.sleep(1)

    final_json_string = json.dumps(base_json_dict, indent=4, ensure_ascii=False)
    print(final_json_string)
    f.write(final_json_string)
