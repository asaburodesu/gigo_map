import requests
from bs4 import BeautifulSoup
import time
import re
import json
from datetime import datetime
from urllib.parse import urljoin

def scrape_gigo_final_complete(max_count=None):
    start_time = datetime.now()
    print(f"処理開始: {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}")

    base_url = "https://www.gendagigo.jp/shop.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(base_url, headers=headers, timeout=30)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"一覧取得エラー: {e}")
        return None

    values = [["タイムスタンプ", "カテゴリ", "画像", "緯度", "経度", "スポット名", "紹介文", "Instagram", "Twitter", "公式サイト", "Facebook"]]
    pref_list = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]

    # 対象店舗数の事前カウント
    total_shops = 0
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 3:
                continue
            if cols[0].get_text(strip=True) == "市区町村":
                continue
            total_shops += 1

    print(f"対象店舗数: {total_shops} 件（一覧ページから検出）")

    count = 0
    skipped_closed = 0
    skipped_unknown_pref = 0
    skipped_no_coords = 0
    skipped_golfbar = 0  # ← 新規追加

    for table in soup.find_all('table'):
        if max_count and count >= max_count:
            break

        current_pref = "不明"
        prev_h = table.find_previous(['h2', 'h3', 'h4'])
        if prev_h:
            text = prev_h.get_text(strip=True)
            for p in pref_list:
                if p in text:
                    current_pref = p
                    break

        rows = table.find_all('tr')
        for row in rows:
            if max_count and count >= max_count:
                break
            cols = row.find_all(['td', 'th'])
            if len(cols) < 3:
                continue

            if cols[0].get_text(strip=True) == "市区町村":
                continue

            count += 1
            shop_cell = cols[1]
            temp_shop_name = shop_cell.get_text(strip=True)
            address = cols[2].get_text(strip=True).replace('\n', ' ').strip()
            link_tag = shop_cell.find('a')

            detail_url = urljoin(base_url, link_tag.get('href')) if link_tag else ""
            lat, lng = "", ""
            final_shop_name = temp_shop_name

            print(f"[{count}/{total_shops}] 解析中: {temp_shop_name} → {detail_url or '(リンクなし)'}")

            if detail_url:
                time.sleep(1.2)

                try:
                    res_d = requests.get(detail_url, headers=headers, timeout=30)
                    res_d.encoding = res_d.apparent_encoding
                    soup_d = BeautifulSoup(res_d.text, 'html.parser')

                    store_name_div = soup_d.find('div', class_='storeName')
                    if store_name_div:
                        strong_tag = store_name_div.find('strong')
                        if strong_tag:
                            final_shop_name = strong_tag.get_text(strip=True)
                            final_shop_name = re.sub(r'\s+', ' ', final_shop_name).strip()
                            discription_p = strong_tag.find('p', class_='discription')
                            if discription_p:
                                kata_name = discription_p.get_text(strip=True)
                                if final_shop_name.startswith(kata_name):
                                    final_shop_name = final_shop_name[len(kata_name):].strip()

                    # 閉店チェック + THE GOLF BAR チェック
                    name_lower = final_shop_name.lower()
                    if any(word in name_lower for word in ['閉店', '閉鎖', 'closed']):
                        print(f"    → 閉店店舗と判断（スキップ）: {final_shop_name}")
                        skipped_closed += 1
                        count -= 1
                        continue

                    if "the golf bar" in name_lower:
                        print(f"    → THE GOLF BAR店舗と判断（スキップ）: {final_shop_name}")
                        skipped_golfbar += 1
                        count -= 1
                        continue

                    # 座標取得部分（変更なし）
                    map_button = soup_d.find('input', {'type': 'button', 'value': 'マップ'})
                    if map_button and 'onclick' in map_button.attrs:
                        onclick_text = map_button['onclick']
                        coord_match = re.search(r'q=([-\d.]+),([-\d.]+)', onclick_text)
                        if coord_match:
                            lat = coord_match.group(1)
                            lng = coord_match.group(2)
                            print(f"    → onclickから座標取得成功: {lat}, {lng}")
                        else:
                            url_match = re.search(r"window\.open\('([^']+)'\)", onclick_text)
                            if url_match:
                                map_url = url_match.group(1)
                                coord_in_url = re.search(r'q=([-\d.]+),([-\d.]+)', map_url)
                                if coord_in_url:
                                    lat, lng = coord_in_url.group(1), coord_in_url.group(2)
                                    print(f"    → window.open URLから座標取得: {lat}, {lng}")

                    if not lat and not lng:
                        iframe = soup_d.find('iframe', src=re.compile(r'(google\.com/maps/embed|maps\.google\.com)'))
                        if iframe:
                            src = iframe.get('src', '')
                            match_3d4d = re.search(r'[!/]3d([-\d.]+)!4d([-\d.]+)', src)
                            if match_3d4d:
                                lat, lng = match_3d4d.group(1), match_3d4d.group(2)
                                print(f"    → iframe (!3d!4d)から: {lat}, {lng}")
                            else:
                                q_match = re.search(r'q=([-\d.]+)%2C([-\d.]+)', src)
                                if q_match:
                                    lat, lng = q_match.group(1), q_match.group(2)
                                    print(f"    → iframe (q=)から: {lat}, {lng}")

                    if not lat and not lng and address:
                        print("    → 座標未取得 → Geocoding検討（未実装）")

                except Exception as e:
                    print(f"    詳細ページエラー: {type(e).__name__}: {e}")

            # スキップ条件
            if current_pref == "不明":
                print(f"    → 都道府県不明のためスキップ: {final_shop_name}")
                skipped_unknown_pref += 1
                count -= 1
                continue

            if not lat or not lng:
                print(f"    → 緯度経度未取得のためスキップ: {final_shop_name} ({lat=}, {lng=})")
                skipped_no_coords += 1
                count -= 1
                continue

            # データ追加
            values.append([
                "",
                current_pref,
                "",
                lat,
                lng,
                final_shop_name,
                address,
                "",
                f"https://twitter.com/intent/tweet?text={final_shop_name}%20{address}",
                detail_url,
                ""
            ])

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
        print(f"\n全件データをJSONファイルとして保存しました: {filename}")
        print(f"保存件数: {len(values) - 1} 件")
        print(f"  └ 閉店スキップ: {skipped_closed} 件")
        print(f"  └ THE GOLF BARスキップ: {skipped_golfbar} 件")
        print(f"  └ 都道府県不明スキップ: {skipped_unknown_pref} 件")
        print(f"  └ 座標未取得スキップ: {skipped_no_coords} 件")
    except Exception as e:
        print(f"JSON保存エラー: {e}")

    print("\n" + "="*50)
    print(f"処理開始: {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
    print(f"処理終了: {end_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
    print(f"所要時間: {duration_str}")
    print("="*50)

    return result


if __name__ == "__main__":
    result = scrape_gigo_final_complete()
    
    print("\n--- 処理完了（JSON保存済み） ---")

