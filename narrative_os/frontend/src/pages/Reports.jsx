import React, { useState, useEffect } from 'react';
import { Users, Link as LinkIcon, BookOpen } from 'lucide-react';
import { api } from '../lib/api';

export default function Reports() {
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('characters'); // 'characters', 'hooks', 'chapters'

  useEffect(() => {
    api.get('/reports/matrix').then(res => {
      setData(res.data);
    });
  }, []);

  if (!data) return <div className="p-8 text-gray-400">正在加载全局大盘数据...</div>;

  return (
    <div className="flex flex-col h-full bg-darker text-gray-200">
      {/* Header & Tabs */}
      <div className="p-8 pb-0 border-b border-gray-800 bg-dark sticky top-0 z-10">
        <h1 className="text-3xl font-bold text-gray-100 mb-6">全局大盘与进展汇总</h1>
        <div className="flex gap-6">
          <button 
            onClick={() => setActiveTab('characters')}
            className={`pb-4 px-2 font-bold text-sm transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'characters' ? 'border-gold text-gold' : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Users size={16} /> 角色线大盘
          </button>
          <button 
            onClick={() => setActiveTab('hooks')}
            className={`pb-4 px-2 font-bold text-sm transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'hooks' ? 'border-orange-500 text-orange-400' : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <LinkIcon size={16} /> 伏笔追踪大盘
          </button>
          <button 
            onClick={() => setActiveTab('chapters')}
            className={`pb-4 px-2 font-bold text-sm transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'chapters' ? 'border-military text-green-400' : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <BookOpen size={16} /> 章节目录大盘
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-8">
        
        {/* Tab 1: 角色线大盘 */}
        {activeTab === 'characters' && (
          <div className="space-y-4 max-w-7xl mx-auto">
            <div className="grid grid-cols-12 gap-4 text-xs font-bold text-gray-500 uppercase tracking-widest px-4 pb-2 border-b border-gray-800">
              <div className="col-span-2">角色 (星级)</div>
              <div className="col-span-5">当前动态状态 (Current Status)</div>
              <div className="col-span-5">静态底色 (Static Core)</div>
            </div>
            {data.characters.map((c, i) => (
              <div key={i} className="grid grid-cols-12 gap-4 bg-dark border border-gray-800 p-4 rounded-xl items-start hover:bg-gray-800/30 transition-colors">
                <div className="col-span-2">
                  <div className="font-bold text-gold text-lg">{c.name}</div>
                  <div className="text-xs text-gray-600 mt-1">{'★'.repeat(c.importance_level)}</div>
                </div>
                <div className="col-span-5 text-sm text-gray-300 leading-relaxed pr-4 border-r border-gray-800">
                  {c.current_status || <span className="text-gray-600 italic">暂无动态状态记录</span>}
                </div>
                <div className="col-span-5 text-xs text-gray-500 leading-relaxed pl-2">
                  {c.static_core}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 2: 伏笔大盘 */}
        {activeTab === 'hooks' && (
          <div className="space-y-4 max-w-5xl mx-auto">
            {data.hooks.length === 0 ? (
              <div className="text-center text-gray-500 py-10">目前暂无伏笔记录</div>
            ) : (
              data.hooks.map((h, i) => (
                <div key={i} className="bg-dark border border-gray-800 p-5 rounded-xl flex gap-6 items-center">
                  <div className="w-32 shrink-0">
                    <div className="text-orange-400 font-bold bg-orange-500/10 px-3 py-1 rounded border border-orange-500/20 text-center text-sm mb-2">
                      {h.hook_code}
                    </div>
                    <div className="text-xs text-center text-gray-500">
                      埋点: 第 {h.planted_in_chapter} 章
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-gray-300 leading-relaxed mb-2">{h.description}</div>
                    {h.status === 'exploded' && (
                      <div className="text-xs text-red-400 bg-red-950/30 p-2 rounded border border-red-900/30 mt-2">
                        <span className="font-bold">引爆后果：</span>{h.resolution || '未记录后果'}
                      </div>
                    )}
                  </div>
                  <div className="w-24 shrink-0 text-center">
                    {h.status === 'sleeping' && <span className="text-gray-500 text-sm">沉睡中</span>}
                    {h.status === 'burning' && <span className="text-orange-500 font-bold text-sm animate-pulse">🔥 燃烧中</span>}
                    {h.status === 'exploded' && <span className="text-red-500 font-bold text-sm">💥 已引爆</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 3: 章节大盘 */}
        {activeTab === 'chapters' && (
          <div className="space-y-6 max-w-6xl mx-auto">
            {data.chapters.length === 0 ? (
              <div className="text-center text-gray-500 py-10">暂无已完成的章节记录，请前往章节控制台进行生成。</div>
            ) : (
              data.chapters.map((c, i) => (
                <div key={i} className="bg-dark border border-gray-800 rounded-xl overflow-hidden shadow-lg">
                  <div className="bg-darker px-6 py-4 border-b border-gray-800 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <span className="text-xl font-bold text-gray-200">第 {c.chapter_no.toString().padStart(3, '0')} 章</span>
                      <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{c.history_date_label}</span>
                    </div>
                    <span className="text-sm text-gray-400">{c.stage_goal}</span>
                  </div>
                  <div className="p-6 grid grid-cols-2 gap-6">
                    <div>
                      <div className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">本章闭环摘要</div>
                      <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                        {c.written_summary}
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">核心资产变动</div>
                        <div className="text-sm text-gold bg-military/10 border border-military/20 p-3 rounded-lg leading-relaxed">
                          {c.key_assets_change || '无重大资产变动'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">留给下章的钩子</div>
                        <div className="text-sm text-orange-300 border-l-2 border-orange-500/50 pl-3 py-1">
                          {c.next_hook || '未留钩子'}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
