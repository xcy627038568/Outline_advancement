import React, { useState, useEffect } from 'react';
import { Folder, FileText, ChevronRight, ChevronDown } from 'lucide-react';
import { api } from '../lib/api';

export default function Outline() {
  const [tree, setTree] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [content, setContent] = useState('');
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    api.get('/outline/tree')
      .then(res => setTree(res.data))
      .catch(err => console.error(err));
  }, []);

  const toggleExpand = (idx) => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const loadFile = (path) => {
    setSelectedFile(path);
    api.get(`/outline/content?path=${encodeURIComponent(path)}`)
      .then(res => setContent(res.data.content))
      .catch(err => setContent("加载失败：" + err.message));
  };

  return (
    <div className="flex h-full">
      {/* 左侧：树形目录 */}
      <div className="w-1/3 bg-dark border-r border-gray-800 p-4 overflow-y-auto">
        <h2 className="text-xl font-bold text-gray-200 mb-6 border-b border-gray-800 pb-2">
          大纲结构 (分卷细纲)
        </h2>
        <div className="space-y-2 text-sm text-gray-300">
          {tree.map((vol, i) => (
            <div key={i} className="select-none">
              <div 
                className="flex items-center gap-2 py-2 px-2 hover:bg-gray-800/50 rounded cursor-pointer"
                onClick={() => toggleExpand(i)}
              >
                {expanded[i] ? <ChevronDown size={16} className="text-gray-500" /> : <ChevronRight size={16} className="text-gray-500" />}
                <Folder size={18} className="text-gold" />
                <span className="font-bold">{vol.name}</span>
              </div>
              
              {expanded[i] && (
                <div className="ml-6 mt-1 space-y-1 border-l border-gray-800 pl-2">
                  {vol.summary_file && (
                    <div 
                      className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer ${selectedFile === vol.path + '/' + vol.summary_file ? 'bg-military/40 text-gold' : 'hover:bg-gray-800/50'}`}
                      onClick={() => loadFile(vol.path + '/' + vol.summary_file)}
                    >
                      <FileText size={14} className="text-blue-400" />
                      {vol.summary_file}
                    </div>
                  )}
                  {vol.units.map((unit, j) => (
                    <div 
                      key={j}
                      className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer ${selectedFile === unit.path ? 'bg-military/40 text-gold' : 'hover:bg-gray-800/50'}`}
                      onClick={() => loadFile(unit.path)}
                    >
                      <FileText size={14} className="text-green-400" />
                      {unit.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 右侧：Markdown 内容预览 */}
      <div className="flex-1 bg-darker p-8 overflow-y-auto">
        {selectedFile ? (
          <div>
            <div className="text-xs text-gray-500 mb-4 pb-2 border-b border-gray-800 font-mono">
              {selectedFile}
            </div>
            <pre className="whitespace-pre-wrap font-sans text-gray-300 leading-relaxed">
              {content}
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600">
            请在左侧选择大纲文件进行预览
          </div>
        )}
      </div>
    </div>
  );
}
