import React, { useState, useEffect } from 'react';
import { Loader2, Flame, Moon, CheckCircle } from 'lucide-react';
import { api } from '../lib/api';

function Hooks() {
  const [hooks, setHooks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/hooks')
      .then(res => res.data)
      .then(data => {
        setHooks(data);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex justify-center items-center h-full">
        <Loader2 className="animate-spin text-gold" size={48} />
      </div>
    );
  }

  // 状态分组
  const groupedHooks = {
    '燃烧中': hooks.filter(h => h.status === '燃烧中' || h.status === 'burning'),
    '沉睡': hooks.filter(h => h.status === '沉睡' || h.status === 'sleeping'),
    '已引爆': hooks.filter(h => h.status === '已引爆' || h.status === 'resolved' || h.status === '已回收'),
  };

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gold">伏笔控制台 (Hooks Kanban)</h1>
        <p className="text-gray-400 mt-1">掌握所有短中长线伏笔的状态流转</p>
      </div>

      <div className="flex-1 grid grid-cols-3 gap-6 overflow-hidden">
        {/* 燃烧中 Column */}
        <div className="bg-dark rounded-xl border border-red-900/30 flex flex-col">
          <div className="p-4 border-b border-red-900/30 bg-red-900/10 flex items-center justify-between">
            <h2 className="font-bold text-red-400 flex items-center gap-2">
              <Flame size={18} /> 燃烧中 (Burning)
            </h2>
            <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-sm">{groupedHooks['燃烧中'].length}</span>
          </div>
          <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3">
            {groupedHooks['燃烧中'].map(h => (
              <HookCard key={h.id} hook={h} color="red" />
            ))}
          </div>
        </div>

        {/* 沉睡 Column */}
        <div className="bg-dark rounded-xl border border-gray-800 flex flex-col">
          <div className="p-4 border-b border-gray-800 bg-gray-800/30 flex items-center justify-between">
            <h2 className="font-bold text-gray-300 flex items-center gap-2">
              <Moon size={18} /> 沉睡 (Sleeping)
            </h2>
            <span className="bg-gray-700 text-gray-300 px-2 py-0.5 rounded text-sm">{groupedHooks['沉睡'].length}</span>
          </div>
          <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3">
            {groupedHooks['沉睡'].map(h => (
              <HookCard key={h.id} hook={h} color="gray" />
            ))}
          </div>
        </div>

        {/* 已引爆 Column */}
        <div className="bg-dark rounded-xl border border-green-900/30 flex flex-col">
          <div className="p-4 border-b border-green-900/30 bg-green-900/10 flex items-center justify-between">
            <h2 className="font-bold text-green-400 flex items-center gap-2">
              <CheckCircle size={18} /> 已引爆 (Resolved)
            </h2>
            <span className="bg-green-500/20 text-green-400 px-2 py-0.5 rounded text-sm">{groupedHooks['已引爆'].length}</span>
          </div>
          <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3">
            {groupedHooks['已引爆'].map(h => (
              <HookCard key={h.id} hook={h} color="green" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function HookCard({ hook, color }) {
  const colorMap = {
    red: 'border-red-900/50 bg-red-900/10 hover:border-red-500/50',
    gray: 'border-gray-700 bg-gray-800/20 hover:border-gray-500',
    green: 'border-green-900/50 bg-green-900/10 hover:border-green-500/50',
  };

  return (
    <div className={`p-4 rounded-lg border transition-colors ${colorMap[color]} cursor-pointer`}>
      <div className="flex justify-between items-start mb-2">
        <div className="text-xs font-mono text-gold bg-gold/10 px-1.5 py-0.5 rounded">
          {hook.hook_code || `HK-${hook.id}`}
        </div>
        <div className="text-xs text-gray-500">
          起于: 第{hook.planted_in_chapter}章
        </div>
      </div>
      <h3 className="font-bold text-gray-200 mb-2">{hook.name || hook.description?.substring(0,20)}</h3>
      <p className="text-sm text-gray-400 line-clamp-3 mb-3">{hook.description}</p>
      
      {hook.resolution && (
        <div className="mt-2 pt-2 border-t border-gray-700/50">
          <p className="text-xs text-green-400/80">
            <span className="font-bold">收尾 (第{hook.resolved_in_chapter}章):</span> {hook.resolution}
          </p>
        </div>
      )}
    </div>
  );
}

export default Hooks;
