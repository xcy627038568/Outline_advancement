import React, { useState, useEffect } from 'react';
import { ShieldAlert, TrendingUp } from 'lucide-react';
import { api } from '../lib/api';

export default function Assets() {
  const [assets, setAssets] = useState([]);

  useEffect(() => {
    api.get('/assets').then(res => {
      setAssets(res.data);
    });
  }, []);

  // 按照 asset_type 进行分组
  const groupedAssets = assets.reduce((acc, asset) => {
    if (!acc[asset.asset_type]) acc[asset.asset_type] = [];
    acc[asset.asset_type].push(asset);
    return acc;
  }, {});

  return (
    <div className="p-10 h-full overflow-y-auto text-gray-200">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-gold mb-10 pb-4 border-b border-gray-800 flex items-center justify-between">
          <span>赵王府资产负债表</span>
          <span className="text-lg text-gray-500 font-normal tracking-widest uppercase">Wealth & Assets</span>
        </h1>

        {Object.entries(groupedAssets).map(([type, items]) => (
          <div key={type} className="mb-12">
            <h2 className="text-2xl font-bold text-gray-300 mb-6 flex items-center gap-3">
              <span className="w-1.5 h-6 bg-military rounded-full shadow-[0_0_10px_rgba(75,83,32,0.6)]"></span> 
              {type}
            </h2>
            <div className="grid grid-cols-3 gap-6">
              {items.map(a => (
                <div key={a.id} className="bg-dark border border-gray-800 p-6 rounded-2xl shadow-xl hover:border-gray-600 transition-all hover:-translate-y-1 hover:shadow-2xl">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="font-bold text-xl text-gray-100 truncate pr-4">{a.asset_name}</h3>
                    <span className="bg-darker text-gray-500 text-xs px-2 py-1 rounded-md border border-gray-700 shadow-inner">
                      Ch.{a.last_update_chapter}
                    </span>
                  </div>
                  
                  <div className="text-3xl font-mono font-bold text-gold mb-6 tracking-tight flex items-center gap-2">
                    <TrendingUp size={20} className="text-military opacity-70" />
                    {a.current_value}
                  </div>
                  
                  {a.hidden_risk && (
                    <div className="mt-4 text-red-400/90 text-sm bg-red-950/20 p-4 rounded-xl border border-red-900/30 flex items-start gap-3 shadow-inner">
                      <ShieldAlert size={18} className="mt-0.5 shrink-0 text-red-500" />
                      <span className="leading-relaxed font-medium tracking-wide">
                        风险：{a.hidden_risk}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {assets.length === 0 && (
          <div className="text-center text-gray-500 py-20 text-xl font-serif">
            暂无资产记录，主角家徒四壁。
          </div>
        )}
      </div>
    </div>
  );
}
