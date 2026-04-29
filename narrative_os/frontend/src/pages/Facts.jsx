import React, { useState, useEffect } from 'react';
import { Loader2, Search, Book, Hash, Clock, MapPin, Scale, Coins } from 'lucide-react';
import { api } from '../lib/api';

function Facts() {
  const [facts, setFacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState('全部');

  useEffect(() => {
    api.get('/facts')
      .then(res => res.data)
      .then(data => {
        setFacts(data);
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

  // 提取唯一类别
  const categories = ['全部', ...new Set(facts.map(f => f.category))];

  // 图标映射
  const getIcon = (category) => {
    if (category.includes('物价')) return <Coins size={16} />;
    if (category.includes('称谓')) return <Hash size={16} />;
    if (category.includes('时间') || category.includes('历史')) return <Clock size={16} />;
    if (category.includes('地理')) return <MapPin size={16} />;
    if (category.includes('法度') || category.includes('规矩')) return <Scale size={16} />;
    return <Book size={16} />;
  };

  const filteredFacts = facts.filter(f => {
    const matchesSearch = 
      f.fact_key.toLowerCase().includes(searchTerm.toLowerCase()) || 
      (f.fact_value && f.fact_value.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (f.description && f.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesCategory = activeCategory === '全部' || f.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gold">世界规则库 (Facts Dictionary)</h1>
          <p className="text-gray-400 mt-1">全局设定、物价标尺与历史事件锚点</p>
        </div>
        <div className="relative">
          <input
            type="text"
            placeholder="搜索规则、物价、地点..."
            className="pl-10 pr-4 py-2 bg-dark border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-gold w-64"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Search className="absolute left-3 top-2.5 text-gray-500" size={18} />
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors flex items-center gap-2 ${
              activeCategory === cat
                ? 'bg-gold text-dark'
                : 'bg-dark border border-gray-700 text-gray-400 hover:text-gold hover:border-gold'
            }`}
          >
            {activeCategory === cat && getIcon(cat)}
            {cat}
          </button>
        ))}
      </div>

      <div className="flex-1 bg-dark rounded-xl border border-gray-800 overflow-hidden flex flex-col">
        <div className="grid grid-cols-4 bg-gray-800/50 p-4 border-b border-gray-700 text-sm font-bold text-gray-300 uppercase">
          <div className="col-span-1">规则键 (Key)</div>
          <div className="col-span-1">数值/定义 (Value)</div>
          <div className="col-span-2">描述 (Description)</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {filteredFacts.length === 0 ? (
            <div className="p-8 text-center text-gray-500">没有找到匹配的规则</div>
          ) : (
            <div className="divide-y divide-gray-800">
              {filteredFacts.map((fact) => (
                <div key={fact.id} className="grid grid-cols-4 p-4 hover:bg-gray-800/30 transition-colors group">
                  <div className="col-span-1 font-mono text-gold flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-gold/50 rounded-full inline-block"></span>
                    {fact.fact_key}
                  </div>
                  <div className="col-span-1 text-gray-300">
                    {fact.fact_value || <span className="text-gray-600 italic">无</span>}
                  </div>
                  <div className="col-span-2 text-gray-400 text-sm">
                    {fact.description}
                    {fact.reference_chapter && (
                      <span className="ml-2 px-1.5 py-0.5 bg-military/30 text-gold/70 rounded text-xs">
                        出处: 第{fact.reference_chapter}章
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Facts;
