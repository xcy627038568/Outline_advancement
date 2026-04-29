import React, { useState, useEffect } from 'react';
import { Tag, Lock, Edit3 } from 'lucide-react';
import { api } from '../lib/api';

export default function Entities() {
  const [entities, setEntities] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get('/entities').then(res => {
      setEntities(res.data);
    });
  }, []);

  return (
    <div className="flex h-full text-gray-200">
      {/* 列表区 */}
      <div className="w-96 bg-dark border-r border-gray-800 p-6 overflow-y-auto">
        <h2 className="text-2xl font-bold text-gray-100 mb-6 border-b border-gray-800 pb-4 flex justify-between items-center">
          实体档案 <span className="text-sm font-normal text-gray-500 bg-gray-800 px-2 py-1 rounded">{entities.length}</span>
        </h2>
        <div className="flex flex-col gap-3">
          {entities.map(e => (
            <div 
              key={e.id}
              onClick={() => setSelected(e)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                selected?.id === e.id 
                  ? 'bg-military/30 border-military/50 shadow-[0_0_15px_rgba(75,83,32,0.2)]' 
                  : 'bg-darker border-gray-800 hover:border-gray-600 hover:bg-gray-800/30'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <span className="font-bold text-lg text-gold">{e.name}</span>
                <span className="text-xs bg-gray-800 text-gray-400 px-2 py-1 rounded border border-gray-700">{e.entity_type}</span>
              </div>
              <div className="text-sm text-gray-400 mb-3 truncate">{'★'.repeat(e.importance_level)}{'☆'.repeat(5-e.importance_level)}</div>
              <div className="text-xs text-gray-300 bg-gray-800/50 p-2 rounded truncate border border-gray-700/50">
                {e.current_status || '暂无动态状态'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 详情区 */}
      <div className="flex-1 bg-darker p-10 overflow-y-auto relative">
        {selected ? (
          <div className="max-w-4xl mx-auto">
            <div className="mb-10 pb-6 border-b border-gray-800 flex justify-between items-end">
              <div>
                <h1 className="text-5xl font-bold text-gold mb-3 tracking-tight">{selected.name}</h1>
                <div className="flex gap-3 text-sm text-gray-400">
                  <span className="bg-dark px-3 py-1 rounded-full border border-gray-700 uppercase tracking-wider">{selected.entity_type}</span>
                  <span className="bg-dark px-3 py-1 rounded-full border border-gray-700 uppercase tracking-wider">最后更新: 第 {selected.last_update_chapter} 章</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-8">
              {/* 静态底色 (不可改) */}
              <div className="bg-dark border border-gray-800 p-6 rounded-2xl relative overflow-hidden shadow-xl">
                <div className="absolute top-4 right-4 text-gray-600 bg-darker p-1.5 rounded-md border border-gray-800">
                  <Lock size={18} />
                </div>
                <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <span className="w-1 h-4 bg-gray-600 rounded-full"></span> 静态底色 (Read-only)
                </h3>
                <div className="text-gray-400 text-sm leading-relaxed whitespace-pre-wrap opacity-80">
                  {selected.static_core}
                </div>
              </div>

              <div className="flex flex-col gap-8">
                {/* 动态状态 (可改) */}
                <div className="bg-dark border border-military/30 p-6 rounded-2xl shadow-[0_0_20px_rgba(75,83,32,0.1)] relative">
                  <div className="absolute top-4 right-4 text-military bg-military/10 p-1.5 rounded-md border border-military/20">
                    <Edit3 size={18} />
                  </div>
                  <h3 className="text-sm font-bold text-military uppercase tracking-widest mb-4 flex items-center gap-2">
                    <span className="w-1 h-4 bg-military rounded-full"></span> 动态状态 (Editable)
                  </h3>
                  <textarea 
                    className="w-full h-32 bg-darker border border-gray-700 rounded-lg p-4 text-gray-200 text-sm focus:outline-none focus:border-military/50 focus:ring-1 focus:ring-military/50 transition-all resize-none"
                    defaultValue={selected.current_status || ''}
                    placeholder="角色在最新一章结束时的心态与处境..."
                  />
                  <div className="mt-3 flex justify-end">
                    <button className="bg-military/20 hover:bg-military/40 text-military font-bold text-sm px-4 py-2 rounded-lg border border-military/30 transition-colors">
                      保存状态
                    </button>
                  </div>
                </div>

                {/* 记忆库 (Tags) */}
                <div className="bg-dark border border-gray-800 p-6 rounded-2xl shadow-xl">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                    <span className="w-1 h-4 bg-blue-500/50 rounded-full"></span> 核心记忆 (Core Memories)
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selected.core_memories ? selected.core_memories.split(';').map((m, i) => (
                      <span key={i} className="bg-blue-900/20 text-blue-300 text-sm px-3 py-1.5 rounded-md border border-blue-900/50 flex items-center gap-2 shadow-sm">
                        <Tag size={14} className="opacity-70" /> {m.trim()}
                      </span>
                    )) : (
                      <span className="text-gray-600 text-sm italic">暂无关键认知解锁</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500 font-serif text-lg">
            在左侧选择实体以查看机密档案
          </div>
        )}
      </div>
    </div>
  );
}
