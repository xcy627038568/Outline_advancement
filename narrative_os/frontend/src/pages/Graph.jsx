import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Loader2 } from 'lucide-react';
import { api } from '../lib/api';

function Graph() {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef(null);

  useEffect(() => {
    api.get('/relationships')
      .then(res => res.data)
      .then(data => {
        // Transform id to string to match ForceGraph expectations if needed
        const nodes = data.nodes.map(n => ({ ...n, id: String(n.id) }));
        const links = data.links.map(l => ({ 
          ...l, 
          source: String(l.source), 
          target: String(l.target) 
        }));
        setData({ nodes, links });
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      setDimensions({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight
      });
    }
    
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 自定义节点绘制
  const paintNode = (node, ctx, globalScale) => {
    const label = node.name;
    const fontSize = Math.max(12 / globalScale, 4);
    ctx.font = `${fontSize}px Sans-Serif`;
    const textWidth = ctx.measureText(label).width;
    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    // 颜色根据实体类型区分
    if (node.entity_type === '角色') {
      ctx.fillStyle = '#D4AF37'; // 核心人物暗金
    } else if (node.entity_type === '派系/组织') {
      ctx.fillStyle = '#4B5320'; // 派系军绿
    } else {
      ctx.fillStyle = '#A0AEC0'; // 其他灰
    }
    
    ctx.fillText(label, node.x, node.y);
    node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
  };

  const paintNodePointerArea = (node, color, ctx) => {
    ctx.fillStyle = color;
    const bckgDimensions = node.__bckgDimensions;
    bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
  };

  if (loading) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-gold" size={48} />
      </div>
    );
  }

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gold">关系网图谱 (Force Graph)</h1>
          <p className="text-gray-400 mt-1">全局势力与人物羁绊拓扑图</p>
        </div>
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2"><span className="w-3 h-3 bg-gold inline-block rounded-full"></span> 角色</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 bg-military inline-block rounded-full"></span> 派系/组织</div>
        </div>
      </div>
      
      <div className="flex-1 bg-dark rounded-xl border border-gray-800 overflow-hidden" ref={containerRef}>
        <ForceGraph2D
          width={dimensions.width}
          height={dimensions.height}
          graphData={data}
          nodeLabel={(node) => `【${node.entity_type}】${node.name}\n重要度: ${node.importance_level}\n状态: ${node.current_state || '无'}`}
          linkLabel={(link) => `【${link.relationship_type}】\n强度: ${link.strength}\n说明: ${link.description || '无'}`}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={paintNodePointerArea}
          linkColor={(link) => {
            if (link.relationship_type === '敌对' || link.relationship_type === '杀意') return 'rgba(239, 68, 68, 0.6)'; // red
            if (link.relationship_type === '盟友' || link.relationship_type === '效忠') return 'rgba(16, 185, 129, 0.6)'; // green
            return 'rgba(156, 163, 175, 0.4)'; // gray
          }}
          linkWidth={link => Math.max(1, link.strength / 20)}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          backgroundColor="#111827"
        />
      </div>
    </div>
  );
}

export default Graph;
