import React, { useState, useEffect } from 'react';
import { AlertCircle, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../lib/api';

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get('/dashboard/alerts').then(res => {
      setData(res.data);
    });
  }, []);

  if (!data) return <div className="p-8 text-gray-400">正在接入大明内阁机密档案...</div>;

  return (
    <div className="p-8 h-full overflow-y-auto">
      <h1 className="text-3xl font-bold text-gray-100 mb-8 border-b border-gray-800 pb-4">
        战局总览
      </h1>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-dark border border-gray-800 p-6 rounded-xl shadow-lg">
          <div className="text-sm text-gray-400 mb-2">当前进度</div>
          <div className="text-2xl font-bold text-gold mb-1">
            第 {data.latest_chapter?.chapter_no ? data.latest_chapter.chapter_no.toString().padStart(3, '0') : '000'} 章
          </div>
          <div className="text-gray-300 text-sm">
            时间轴：{data.latest_chapter?.history_date_label || '未初始化'}
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-green-500 bg-green-500/10 w-fit px-3 py-1 rounded-full border border-green-500/20">
            <CheckCircle2 size={16} /> 已入库
          </div>
        </div>

        <div className="col-span-2 bg-dark border border-blue-900/50 p-6 rounded-xl shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl rounded-full"></div>
          <div className="text-sm text-blue-400 mb-4 flex items-center gap-2 font-bold">
            <AlertCircle size={18} /> 系统状态 (V4 细纲驱动)
          </div>
          {data.alerts.length === 0 ? (
            <div className="text-gray-400">当前已进入细纲驱动模式，资产与状态无需强行更新。</div>
          ) : (
            <div className="flex flex-col gap-3">
              {data.alerts.map((a, i) => (
                <div key={i} className="bg-red-500/10 border border-red-500/20 text-red-200 px-4 py-3 rounded-lg text-sm">
                  {a.msg}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h2 className="text-xl font-bold text-gray-200 mb-4 flex items-center gap-2">
            🔥 当前活跃伏笔
          </h2>
          <div className="bg-dark border border-gray-800 rounded-xl overflow-hidden">
            {data.burning_hooks.length === 0 ? (
              <div className="p-6 text-gray-500 text-center">暂无燃烧中的伏笔</div>
            ) : (
              data.burning_hooks.map((h, i) => (
                <div key={i} className="p-4 border-b border-gray-800 last:border-0 hover:bg-gray-800/30 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-orange-400 font-bold text-sm bg-orange-500/10 px-2 py-1 rounded border border-orange-500/20">
                      {h.hook_code}
                    </span>
                    <span className="text-xs text-gray-500">埋于第 {h.planted_in_chapter} 章</span>
                  </div>
                  <div className="text-gray-300 text-sm leading-relaxed">{h.description}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div>
          <h2 className="text-xl font-bold text-gray-200 mb-4 flex items-center gap-2">
            💰 主角资产快照
          </h2>
          <div className="bg-dark border border-gray-800 rounded-xl p-6 grid grid-cols-2 gap-4">
            {data.assets.slice(0, 4).map((a, i) => (
              <div key={i} className="bg-darker border border-gray-800 p-4 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">{a.asset_type}</div>
                <div className="font-bold text-gray-200 mb-2 truncate">{a.asset_name}</div>
                <div className="text-gold font-mono text-lg truncate">{a.current_value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
