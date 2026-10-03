/**
 * @file 公開中の data.json を取得し public/data.json として保存する（ローカル開発用）
 */

const fs = require("fs");
const path = require("path");

const dataUrl = "https://asaburodesu.github.io/gigo_map/data.json";
const distDataFilePath = path.join(process.cwd(), "/public/data.json");

(async () => {
  let res;
  try {
    res = await fetch(dataUrl);
  } catch (error) {
    process.stderr.write(`${dataUrl} の取得に失敗しました: ${error.message}\n`);
    process.exit(1);
  }

  if (!res.ok) {
    process.stderr.write(`${dataUrl} の取得に失敗しました: HTTP ${res.status}\n`);
    process.exit(1);
  }

  const text = await res.text();
  try {
    JSON.parse(text);
  } catch (error) {
    process.stderr.write(`${dataUrl} は正しい JSON 形式ではありません。\n`);
    process.exit(2);
  }

  fs.writeFileSync(distDataFilePath, text);
  process.stdout.write(`${distDataFilePath} を保存しました。\n`);
})();
