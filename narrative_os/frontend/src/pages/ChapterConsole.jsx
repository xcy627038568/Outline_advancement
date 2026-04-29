import React, { useState, useEffect } from 'react';
import { Search, ChevronRight, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api';

export default function ChapterConsole() {
  const [chapters, setChapters] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get('/chapters').then(res => {
      setChapters(res.data);
      if (res.data.length > 0) setSelected(res.data[0]);
    });
  }, []);

  const loadChapter = (chapter) => {
    api.get(`/chapters/${chapter.chapter_no}`).then(res => {
      setSelected(res.data);
    });
  };

  return (
    <div className="flex h-full overflow-hidden text-gray-200">
      {/* 左侧导航 */}
      <div className="w-80 bg-dark border-r border-gray-800 flex flex-col h-full shrink-0">
        <div className="p-4 border-b border-gray-800 bg-darker/50 sticky top-0 z-10 backdrop-blur-sm">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 text-gray-500" size={18} />
            <input 
              type="text" 
              placeholder="搜索章节..." 
              className="w-full bg-darker border border-gray-700 rounded-lg py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-military/50 transition-colors"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {chapters.map(c => (
            <button
              key={c.chapter_no}
              onClick={() => loadChapter(c)}
              className={`w-full text-left px-4 py-3 rounded-lg mb-1 flex items-center justify-between group transition-all ${
                selected?.chapter_no === c.chapter_no 
                  ? 'bg-military/30 border border-military/50 shadow-[0_0_15px_rgba(75,83,32,0.2)]' 
                  : 'hover:bg-gray-800/50 border border-transparent'
              }`}
            >
              <div>
                <div className="font-bold text-gray-200 flex items-center gap-2 flex-wrap">
                  <span className="whitespace-nowrap">第 {c.chapter_no.toString().padStart(3, '0')} 章</span>
                  {c.title && <span className="text-gray-400 font-normal truncate max-w-[140px] text-sm" title={c.title}>{c.title}</span>}
                  {c.status === 'written' && <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] shrink-0"></span>}
                  {c.status === 'pending' && <span className="w-2 h-2 rounded-full bg-gray-600 shrink-0"></span>}
                </div>
              </div>
              <ChevronRight size={16} className={`text-gray-600 group-hover:text-gold transition-colors ${selected?.chapter_no === c.chapter_no ? 'text-gold opacity-100' : 'opacity-0'}`} />
            </button>
          ))}
        </div>
      </div>

      {/* 中间详情：左右分栏对比 */}
      <div className="flex-1 flex overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-military/10 to-transparent pointer-events-none z-0"></div>
        {selected ? (
          <>
            {/* 左侧分栏：正文内容 (Chapter Content) */}
            <div className="w-4/5 overflow-y-auto p-8 border-r border-gray-800 bg-darker/50 z-10">
              <div className="mb-6 border-b border-gray-800 pb-4">
                <span className="text-gold font-mono tracking-tight text-sm mb-2 block">{selected.timeline_mark || selected.history_date_label || '时间轴待定'}</span>
                <h2 className="text-2xl font-bold text-gray-100 mb-2">
                  第 {selected.chapter_no.toString().padStart(3, '0')} 章 {selected.title ? ` ${selected.title}` : ''} (正文展示)
                </h2>
              </div>

              <div className="space-y-6">
                <section className="bg-dark border border-gray-800 rounded-xl p-6 shadow-lg h-full">
                  <h3 className="text-xs font-bold text-military uppercase tracking-widest mb-3 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-military rounded-full"></span>
                    定稿正文
                  </h3>
                  <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap break-words font-serif bg-darker p-4 rounded border border-gray-800 min-h-[500px] w-full">
                    {selected.chapter_content || '该章节尚未生成正文。'}
                  </div>
                </section>
              </div>
            </div>

            {/* 右侧分栏：实际生成 (Generated) */}
            <div className="w-1/5 overflow-y-auto p-8 bg-darker z-10">
              <div className="mb-6 border-b border-gray-800 pb-4 flex justify-between items-end">
                <h2 className="text-2xl font-bold text-gray-100 mb-2">实际生成结果</h2>
                {selected.status === 'written' ? (
                  <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/30 rounded-full text-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> 已闭环
                  </span>
                ) : (
                  <span className="px-3 py-1 bg-gray-800 text-gray-400 border border-gray-700 rounded-full text-xs">
                    等待生成
                  </span>
                )}
              </div>

              <div className="space-y-6">
                <section className="bg-dark border border-gray-800 rounded-xl p-6 shadow-lg">
                  <h3 className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                    生成摘要 (Written Summary)
                  </h3>
                  <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                    {selected.written_summary || <span className="text-gray-600 italic">暂无内容</span>}
                  </div>
                </section>

                <section className="bg-dark border border-gray-800 rounded-xl p-6 shadow-lg">
                  <h3 className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">
                    下一章钩子 (Next Hook)
                  </h3>
                  <div className="text-gray-300 text-sm leading-relaxed">
                    {selected.next_hook || <span className="text-gray-600 italic">—</span>}
                  </div>
                </section>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center w-full h-full text-gray-500 font-serif text-lg z-10">
            在左侧选择章节以展开战术推演
          </div>
        )}
      </div>
    </div>
  );
}
