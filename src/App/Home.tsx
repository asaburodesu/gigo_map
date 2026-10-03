import React from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { AiOutlineClose } from 'react-icons/ai'
import { FaList } from "react-icons/fa"
import Map from "./Map"
import './Home.scss'

type Props = {
  data: Pwamap.ShopData[];
}

const Content = (props: Props) => {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  // 地図以外のページを表示している間は、地図を作り直さずに隠しておく
  const isActive = location.pathname === '/'
  const queryCategory = isActive ? searchParams.get('category') : null

  // 都道府県が指定されている場合はその店舗だけを地図に表示する
  const data = React.useMemo(() => {
    if (!queryCategory) {
      return props.data
    }
    return props.data.filter((shop) => {
      return shop['カテゴリ'] === queryCategory
    })
  }, [props.data, queryCategory])

  return (
    <div className={`home${isActive ? '' : ' inactive'}${queryCategory ? ' has-category' : ''}`}>
      {/* 絞り込みを解除したときは表示位置をそのままにする */}
      <Map data={data} keepView={!queryCategory} />
      {queryCategory &&
        <div className="map-category">
          <span className="map-category-label">{`${queryCategory}（${data.length}件）`}</span>
          <Link to={`/list?category=${encodeURIComponent(queryCategory)}`}><FaList size="14px" color="#FFFFFF" /> 一覧</Link>
          <Link to="/"><AiOutlineClose size="16px" color="#FFFFFF" /> 解除</Link>
        </div>
      }
    </div>
  );
};

export default Content;
