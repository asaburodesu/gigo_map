import './AboutUs.scss';
import config from '../config.json';
import { FaPlus } from 'react-icons/fa';
import { useState, useEffect } from 'react';

const Content = () => {
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    const fetchLastUpdate = async () => {
      try {
        const response = await fetch('https://asaburodesu.github.io/imas_map/last_update.json?timestamp=' + new Date().getTime(), {
          cache: 'no-cache', // キャッシュを無効にする
        });
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        setLastUpdate(data.last_update);
      } catch (error) {
        console.error('Fetching last update failed:', error);
        setLastUpdate('情報の取得に失敗しました'); // エラーメッセージを設定
      }
    };

    fetchLastUpdate();
  }, []); // 最初にコンポーネントがマウントされたときに一度だけ実行

  const clickHandler = () => {
    if (config.form_url) {
      window.location.href = config.form_url;
    }
  };

  return (
    <div className="about-us">
      <div className="container">
        <div className="branding">
          <div className="logo">アイドルマスターツアーズ設置店舗マップ</div>
        </div>

        <h2>このマップについて</h2>
        <p>作成者:<a href="https://twitter.com/asaburodesu" target='_blank' rel="noreferrer">asaburodesu</a></p>
        <p>最終更新: {lastUpdate}</p>
        <p>当サイトでは可能な限り情報の正確性を心がけていますが、安全性や確実な情報提供を保証するものではありません。掲載内容で生じた損害（間接的を含む）に対する一切の責任を負いません。</p>
        
        <h2>他機種マップ</h2>
        <p><a href="https://asaburodesu.github.io/chu_map/" target='_blank' rel="noreferrer">CHUNITHM設置店舗マップ</a></p>
        <p><a href="https://asaburodesu.github.io/geki_map/" target='_blank' rel="noreferrer">オンゲキ設置店舗マップ</a></p>
        <p><a href="https://asaburodesu.github.io/mai_map/" target='_blank' rel="noreferrer">maimai設置店舗マップ</a></p>

        {config.form_url?
          <>
            <h2>データの更新について</h2>
            <p>このアプリのデータを更新するには下の「 + 」ボタンを押してフォームに必要な情報を入力してください。</p>
            <div className="goto-form"><button><FaPlus color="#FFFFFF" onClick={clickHandler} /></button></div>
          </>
          :
          <></>
        }
      </div>
    </div>
  );
};

export default Content;
