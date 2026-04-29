import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { BookOpen, Users, Coins, LineChart, Network, Anchor, Globe, FolderTree, Crosshair } from 'lucide-react';
import CurrentChapter from './pages/CurrentChapter';
import ChapterConsole from './pages/ChapterConsole';
import Outline from './pages/Outline';
import Entities from './pages/Entities';
import Assets from './pages/Assets';
import Reports from './pages/Reports';
import Graph from './pages/Graph';
import Hooks from './pages/Hooks';
import Facts from './pages/Facts';
import './App.css';

function Sidebar() {
  const location = useLocation();
  const navItems = [
    { path: '/', label: '当前章作战台', icon: Crosshair },
    { path: '/chapters', label: '章节库', icon: BookOpen },
    { path: '/outline', label: '细纲源文件', icon: FolderTree },
    { path: '/entities', label: '实体档案', icon: Users },
    { path: '/assets', label: '资产大盘', icon: Coins },
    { path: '/graph', label: '关系网图谱', icon: Network },
    { path: '/hooks', label: '伏笔看板', icon: Anchor },
    { path: '/facts', label: '世界规则库', icon: Globe },
    { path: '/reports', label: '全局报告', icon: LineChart },
  ];

  return (
    <div className="app-sidebar w-72 h-screen border-r border-gray-800 p-5 flex flex-col">
      <div className="app-brand text-gold font-bold text-xl mb-8 flex items-center gap-3">
        <span className="app-brand-mark text-2xl">🏮</span>
        <div>
          <div className="app-brand-title">Narrative OS</div>
          <div className="app-brand-subtitle">章节作战中枢</div>
        </div>
      </div>
      <nav className="app-nav flex flex-col gap-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`app-nav-link flex items-center gap-3 px-4 py-3 rounded-xl ${
                isActive ? 'app-nav-link-active text-gold border border-military/50' : 'text-gray-300'
              }`}
            >
              <span className="app-nav-icon">
                <Icon size={18} />
              </span>
              <span className="app-nav-text">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="app-shell flex h-screen text-gray-200 font-sans">
        <Sidebar />
        <div className="app-content flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<CurrentChapter />} />
            <Route path="/dashboard" element={<CurrentChapter />} />
            <Route path="/outline" element={<Outline />} />
            <Route path="/chapters" element={<ChapterConsole />} />
            <Route path="/entities" element={<Entities />} />
            <Route path="/assets" element={<Assets />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/hooks" element={<Hooks />} />
            <Route path="/facts" element={<Facts />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
