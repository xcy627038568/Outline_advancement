import React, { memo, useEffect, useMemo, useRef, useState, useTransition } from 'react';
import {
  BookOpen,
  CheckCircle2,
  Compass,
  FileClock,
  FolderKanban,
  PlayCircle,
  RefreshCw,
  Save,
  ScrollText,
  ShieldAlert,
  Users,
  Wallet,
} from 'lucide-react';
import {
  api,
  finalizeWorkflow,
  generateWorkflowRadar,
  getCurrentWorkflow,
  getWorkflow,
  getWorkflowCharacterContext,
  saveWorkflowDraft,
  saveWorkflowLedger,
} from '../lib/api';
import './CurrentChapter.css';

function StatusBadge({ status }) {
  if (status === 'written') {
    return (
      <span className="px-3 py-1 rounded-full text-xs border border-green-500/30 bg-green-500/15 text-green-300">
        已闭环
      </span>
    );
  }

  return (
    <span className="px-3 py-1 rounded-full text-xs border border-yellow-500/30 bg-yellow-500/10 text-yellow-200">
      待处理
    </span>
  );
}

function Panel({ title, icon: Icon, children, extra, className = '' }) {
  return (
    <section className={`chapter-panel bg-dark border border-gray-800 rounded-2xl p-5 shadow-lg ${className}`}>
      <div className="flex items-center justify-between mb-4 gap-3">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-gold" />
          <h2 className="chapter-panel-title text-sm font-bold tracking-wide text-gray-100">{title}</h2>
        </div>
        {extra}
      </div>
      {children}
    </section>
  );
}

function MarkdownBlock({ content, height = 'max-h-72', className = '' }) {
  return (
    <pre
      className={`chapter-markdown whitespace-pre-wrap text-sm leading-6 text-gray-300 bg-darker border border-gray-800 rounded-xl p-4 overflow-y-auto ${height} ${className}`}
    >
      {content || '暂无内容'}
    </pre>
  );
}

function getErrorMessage(err, fallback) {
  return err.response?.data?.detail || err.message || fallback;
}

function DirtyBadge({ dirty }) {
  return (
    <span
      className={`px-3 py-1 rounded-full text-xs border ${
        dirty
          ? 'border-yellow-500/30 bg-yellow-500/10 text-yellow-200'
          : 'border-gray-700 bg-darker text-gray-400'
      }`}
    >
      {dirty ? '未保存' : '已同步'}
    </span>
  );
}

function CharacterModeHint({ mode }) {
  const textMap = {
    chapter: '当前显示正文实际命中的角色',
    requested: '当前显示主动补申请的角色',
    fallback: '当前正文未命中角色，以下为细纲兜底角色',
    empty: '当前未识别到角色',
  };

  return <div className="text-xs text-gray-500">{textMap[mode] || '当前角色上下文'}</div>;
}

function BusyIndicator({ label }) {
  return (
    <div className="chapter-busy-indicator">
      <span className="chapter-busy-dot" />
      <span>{label}</span>
    </div>
  );
}

const ChapterNavItem = memo(function ChapterNavItem({ item, active, switching, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(item.chapter_no)}
      className={`chapter-nav-item w-full text-left rounded-xl px-4 py-3 mb-2 border ${
        active ? 'chapter-nav-item-active' : 'bg-darker/70 border-gray-800 text-gray-300 hover:bg-gray-800/60'
      } ${switching ? 'chapter-nav-item-switching' : ''}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="font-semibold">第 {item.chapter_no.toString().padStart(3, '0')} 章</div>
        {switching ? (
          <span className="chapter-switch-spinner" aria-hidden="true" />
        ) : (
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              item.status === 'written' ? 'bg-green-500' : 'bg-yellow-500'
            }`}
          />
        )}
      </div>
      <div className="text-xs text-gray-500 mt-1 truncate">{item.title || '未命名章节'}</div>
    </button>
  );
});

function parseRequestedNames(value) {
  return value
    .split(/[、，,\s/\\]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function compactChapterContent(value = '') {
  return value
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+\n/g, '\n\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export default function CurrentChapter() {
  const [chapters, setChapters] = useState([]);
  const [workflow, setWorkflow] = useState(null);
  const [selectedNo, setSelectedNo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [switchingChapterNo, setSwitchingChapterNo] = useState(null);
  const [error, setError] = useState('');
  const [draftBaseline, setDraftBaseline] = useState({ title: '', content: '' });
  const [draftTitle, setDraftTitle] = useState('');
  const [draftContent, setDraftContent] = useState('');
  const [ledgerBaseline, setLedgerBaseline] = useState('');
  const [ledgerContent, setLedgerContent] = useState('');
  const [draftEditMode, setDraftEditMode] = useState(false);
  const [ledgerEditMode, setLedgerEditMode] = useState(false);
  const [characterContext, setCharacterContext] = useState(null);
  const [requestedCharacters, setRequestedCharacters] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionLog, setActionLog] = useState('');
  const [isPending, startTransition] = useTransition();
  const workflowCacheRef = useRef(new Map());
  const preloadSetRef = useRef(new Set());

  const chapter = workflow?.chapter;
  const draftDirty = draftTitle !== draftBaseline.title || draftContent !== draftBaseline.content;
  const ledgerDirty = ledgerContent !== ledgerBaseline;
  const hasUnsavedChanges = draftDirty || ledgerDirty;
  const compactedDraftContent = useMemo(() => compactChapterContent(draftBaseline.content), [draftBaseline.content]);

  const selectedChapterMeta = useMemo(
    () => chapters.find((item) => item.chapter_no === selectedNo),
    [chapters, selectedNo],
  );
  const pageBusy = loading || Boolean(switchingChapterNo);
  const busyLabel = switchingChapterNo
    ? `正在切换到第 ${switchingChapterNo.toString().padStart(3, '0')} 章`
    : loading
      ? '正在刷新作战台'
      : '';

  async function confirmDiscardUnsaved(actionLabel) {
    if (!hasUnsavedChanges) {
      return true;
    }
    return window.confirm(`正文或台账有未保存改动，${actionLabel}会丢失改动，是否继续？`);
  }

  async function loadInitial(skipConfirm = false) {
    if (!skipConfirm) {
      const confirmed = await confirmDiscardUnsaved('刷新当前章');
      if (!confirmed) {
        return;
      }
    }

    setLoading(true);
    setSwitchingChapterNo(null);
    setError('');
    try {
      const [chaptersRes, workflowRes] = await Promise.all([
        api.get('/chapters'),
        getCurrentWorkflow(),
      ]);
      workflowCacheRef.current.set(workflowRes.chapter.chapter_no, workflowRes);
      startTransition(() => {
        setChapters(chaptersRes.data);
        setWorkflow(workflowRes);
        setSelectedNo(workflowRes.chapter.chapter_no);
      });
    } catch (err) {
      setError(getErrorMessage(err, '当前章作战台加载失败'));
    } finally {
      setLoading(false);
    }
  }

  async function loadWorkflow(chapterNo) {
    if (chapterNo === selectedNo && workflow?.chapter?.chapter_no === chapterNo) {
      return;
    }
    const confirmed = await confirmDiscardUnsaved('切换章节');
    if (!confirmed) {
      return;
    }

    setSelectedNo(chapterNo);
    setError('');
    const cachedWorkflow = workflowCacheRef.current.get(chapterNo);

    if (cachedWorkflow) {
      startTransition(() => {
        setWorkflow(cachedWorkflow);
      });
    } else {
      setSwitchingChapterNo(chapterNo);
    }

    try {
      const response = await getWorkflow(chapterNo);
      workflowCacheRef.current.set(chapterNo, response);
      startTransition(() => {
        setWorkflow(response);
      });
    } catch (err) {
      setError(getErrorMessage(err, '章节上下文加载失败'));
    } finally {
      setSwitchingChapterNo(null);
    }
  }

  useEffect(() => {
    loadInitial(true);
  }, []);

  useEffect(() => {
    if (!workflow) {
      return;
    }
    const nextDraft = {
      title: workflow.chapter?.title || workflow.outline?.title || '',
      content: compactChapterContent(workflow.chapter?.chapter_content || ''),
    };
    const nextLedger = workflow.ledger?.content || '';

    setDraftBaseline(nextDraft);
    setDraftTitle(nextDraft.title);
    setDraftContent(nextDraft.content);
    setLedgerBaseline(nextLedger);
    setLedgerContent(nextLedger);
    setDraftEditMode(false);
    setLedgerEditMode(false);
    setCharacterContext(workflow.characters || null);
    setRequestedCharacters('');
    setActionMessage('');
    setActionError('');
    setActionLog('');
  }, [workflow?.chapter?.chapter_no]);

  useEffect(() => {
    if (!selectedNo || chapters.length === 0) {
      return;
    }

    const neighborNos = chapters
      .filter((item) => Math.abs(item.chapter_no - selectedNo) === 1)
      .map((item) => item.chapter_no);

    neighborNos.forEach((chapterNo) => {
      if (workflowCacheRef.current.has(chapterNo) || preloadSetRef.current.has(chapterNo)) {
        return;
      }

      preloadSetRef.current.add(chapterNo);
      getWorkflow(chapterNo)
        .then((response) => {
          workflowCacheRef.current.set(chapterNo, response);
        })
        .catch(() => {})
        .finally(() => {
          preloadSetRef.current.delete(chapterNo);
        });
    });
  }, [chapters, selectedNo]);

  useEffect(() => {
    const handleBeforeUnload = (event) => {
      if (!hasUnsavedChanges) {
        return undefined;
      }
      event.preventDefault();
      event.returnValue = '';
      return '';
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  async function refreshCurrentWorkflow(skipConfirm = false) {
    if (!skipConfirm) {
      const confirmed = await confirmDiscardUnsaved('刷新数据');
      if (!confirmed) {
        return;
      }
    }

    if (!selectedNo) {
      return;
    }
    const [chaptersRes, refreshed] = await Promise.all([
      api.get('/chapters'),
      getWorkflow(selectedNo),
    ]);
    workflowCacheRef.current.set(selectedNo, refreshed);
    startTransition(() => {
      setChapters(chaptersRes.data);
      setWorkflow(refreshed);
    });
  }

  async function runAction(actionKey, runner) {
    setActionLoading(actionKey);
    setActionMessage('');
    setActionError('');
    try {
      const result = await runner();
      setActionMessage(result.message || '操作完成');
      setActionLog(result.stdout || result.message || '');
      return result;
    } catch (err) {
      const message = getErrorMessage(err, '操作失败');
      setActionError(message);
      setActionLog(err.response?.data?.detail || '');
      throw err;
    } finally {
      setActionLoading('');
    }
  }

  async function handleSaveDraft() {
    await runAction('save-draft', async () => {
      const normalizedContent = compactChapterContent(draftContent);
      const result = await saveWorkflowDraft(selectedNo, {
        title: draftTitle,
        content: normalizedContent,
      });
      setDraftTitle(draftTitle);
      setDraftContent(normalizedContent);
      setDraftBaseline({ title: draftTitle, content: normalizedContent });
      setDraftEditMode(false);
      await refreshCurrentWorkflow(true);
      return result;
    });
  }

  async function handleSaveLedger() {
    await runAction('save-ledger', async () => {
      const result = await saveWorkflowLedger(selectedNo, {
        content: ledgerContent,
      });
      setLedgerBaseline(ledgerContent);
      setLedgerEditMode(false);
      await refreshCurrentWorkflow(true);
      return result;
    });
  }

  async function handleFinalize() {
    if (hasUnsavedChanges) {
      setActionError('正文或台账有未保存改动，请先在对应 section 内手动保存，再执行闭环。');
      setActionMessage('');
      return;
    }

    await runAction('finalize', async () => {
      const result = await finalizeWorkflow(selectedNo);
      workflowCacheRef.current.set(selectedNo, result.workflow);
      setWorkflow(result.workflow);
      return {
        message: '章节闭环已执行完成',
        stdout: [result.stdout, result.stderr].filter(Boolean).join('\n'),
      };
    });
  }

  async function handleGenerateRadar() {
    await runAction('generate-radar', async () => {
      const result = await generateWorkflowRadar(selectedNo);
      workflowCacheRef.current.set(selectedNo, result.workflow);
      setWorkflow(result.workflow);
      return {
        message: `第 ${selectedNo?.toString().padStart(3, '0')} 章战术靶点雷达已刷新`,
        stdout: [result.stdout, result.stderr].filter(Boolean).join('\n'),
      };
    });
  }

  async function handleRefreshCharacters() {
    await runAction('refresh-characters', async () => {
      const result = await getWorkflowCharacterContext(selectedNo, {
        chapter_content: draftContent,
        requested_names: parseRequestedNames(requestedCharacters),
      });
      setCharacterContext(result);
      return {
        message: '角色上下文已按当前正文刷新',
        stdout: `命中角色：${result.names?.join('、') || '无'}`,
      };
    });
  }

  function handleDiscardDraft() {
    if (draftDirty && !window.confirm('放弃当前正文修改？')) {
      return;
    }
    setDraftTitle(draftBaseline.title);
    setDraftContent(draftBaseline.content);
    setDraftEditMode(false);
  }

  function handleDiscardLedger() {
    if (ledgerDirty && !window.confirm('放弃当前台账修改？')) {
      return;
    }
    setLedgerContent(ledgerBaseline);
    setLedgerEditMode(false);
  }

  if (loading && !workflow) {
    return <div className="p-8 text-gray-400">正在构建当前章作战台...</div>;
  }

  if (error && !workflow) {
    return <div className="p-8 text-red-300">{error}</div>;
  }

  return (
    <div className="chapter-workbench flex h-full overflow-hidden">
      <aside className="chapter-sidebar w-80 shrink-0 border-r border-gray-800 bg-dark flex flex-col">
        <div className="p-5 border-b border-gray-800">
          <div className="text-xs uppercase tracking-[0.3em] text-gray-500 mb-2">Narrative OS</div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-gray-100">当前章作战台</h1>
              <p className="text-sm text-gray-400 mt-1">围绕本章推进写前情报、正文保存与闭环执行</p>
            </div>
            <button
              type="button"
              onClick={() => loadInitial()}
              className={`chapter-icon-button p-2 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800/70 ${
                loading ? 'chapter-rotating' : ''
              }`}
              title="刷新当前章"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        <div className="p-4 border-b border-gray-800">
          <div className="bg-darker border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">当前聚焦</div>
            <div className="text-lg font-bold text-gold">
              第 {chapter?.chapter_no?.toString().padStart(3, '0') || '000'} 章
            </div>
            <div className="text-sm text-gray-300 mt-1">
              {chapter?.title || selectedChapterMeta?.title || workflow?.outline?.title || '标题待定'}
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {chapter?.timeline_mark || chapter?.history_date_label || '时间线待补'}
            </div>
            <div className="mt-3">
              <StatusBadge status={chapter?.status} />
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="text-xs uppercase tracking-[0.25em] text-gray-500 px-2 mb-2">章节列表</div>
          {chapters.map((item) => (
            <ChapterNavItem
              key={item.chapter_no}
              item={item}
              active={item.chapter_no === selectedNo}
              switching={item.chapter_no === switchingChapterNo}
              onSelect={loadWorkflow}
            />
          ))}
        </div>
      </aside>

      <main className="chapter-main flex-1 overflow-y-auto p-6">
        {pageBusy ? (
          <div className="chapter-loading-overlay" aria-hidden="true">
            <div className="chapter-loading-card">
              <div className="chapter-switch-spinner" />
              <div className="chapter-loading-title">{busyLabel || '正在更新作战台'}</div>
              <div className="chapter-loading-subtitle">已保留当前内容，切换完成后平滑替换。</div>
              <div className="chapter-skeleton-lines">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        ) : null}
        {error ? (
          <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        <div
          className={`chapter-grid chapter-content-shell grid grid-cols-1 xl:grid-cols-[minmax(0,1.52fr)_minmax(320px,0.48fr)] gap-6 ${
            pageBusy ? 'is-busy' : ''
          }`}
        >
          <div className="space-y-6">
            <Panel
              title="本章任务卡"
              icon={CheckCircle2}
              extra={actionLoading ? <BusyIndicator label="执行中..." /> : null}
            >
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-1">章节号</div>
                  <div className="text-2xl font-bold text-gold">{chapter?.chapter_no || '-'}</div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-1">时间线</div>
                  <div className="text-sm text-gray-200 leading-6">
                    {chapter?.timeline_mark || chapter?.history_date_label || '待补'}
                  </div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-1">章节标题</div>
                  <div className="text-sm text-gray-200 leading-6">
                    {chapter?.title || workflow?.outline?.title || '待定'}
                  </div>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleFinalize}
                  disabled={!selectedNo || actionLoading}
                  className="chapter-primary-button inline-flex items-center gap-2 rounded-xl border border-gold/30 bg-gold/10 px-4 py-2 text-sm text-gold hover:bg-gold/20 disabled:opacity-50"
                >
                  <PlayCircle size={16} />
                  一键闭环
                </button>
              </div>
              {actionMessage ? (
                <div className="mt-4 rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm text-green-200">
                  {actionMessage}
                </div>
              ) : null}
              {actionError ? (
                <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200 whitespace-pre-wrap">
                  {actionError}
                </div>
              ) : null}
              <div className="mt-4 grid md:grid-cols-2 gap-4 text-xs text-gray-400">
                <div className="bg-darker border border-gray-800 rounded-xl p-4 break-all">
                  <div className="text-gray-500 mb-1">正文路径</div>
                  {workflow?.files?.chapter_path || '未找到'}
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4 break-all">
                  <div className="text-gray-500 mb-1">台账路径</div>
                  {workflow?.files?.ledger_path || '未生成'}
                </div>
              </div>
            </Panel>

            <Panel
              title="细纲任务"
              icon={BookOpen}
              extra={<StatusBadge status={chapter?.status} />}
            >
              <div className="text-sm text-gray-300 leading-7">
                本页围绕当前章推进正文、角色、资产与闭环，不再直接暴露数据库内部结构。
              </div>
            </Panel>

            <Panel title="本章细纲" icon={FolderKanban}>
              <MarkdownBlock content={workflow?.outline?.content} height="max-h-[22rem]" />
            </Panel>

            <Panel
              title="战术靶点雷达"
              icon={Compass}
              extra={
                <button
                  type="button"
                  onClick={handleGenerateRadar}
                  disabled={!selectedNo || actionLoading}
                  className="chapter-secondary-button rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-800/70 disabled:opacity-50"
                >
                  生成/刷新雷达
                </button>
              }
            >
              {workflow?.radar?.exists ? (
                <MarkdownBlock content={workflow?.radar?.content} height="max-h-[28rem]" />
              ) : (
                <div className="rounded-xl border border-dashed border-gray-700 bg-darker px-4 py-6 text-sm leading-7 text-gray-400">
                  {workflow?.radar?.message || '雷达未生成，请按当前选中章节手动生成。'}
                </div>
              )}
            </Panel>

            <Panel
              title="本章正文"
              icon={ScrollText}
              className="chapter-reading-panel"
              extra={
                <div className="flex items-center gap-2">
                  <DirtyBadge dirty={draftDirty} />
                  {!draftEditMode ? (
                    <button
                      type="button"
                      onClick={() => setDraftEditMode(true)}
                      className="chapter-secondary-button rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-800/70"
                    >
                      编辑正文
                    </button>
                  ) : null}
                </div>
              }
            >
              <div className="space-y-4">
                {draftEditMode ? (
                  <>
                    <div>
                      <div className="text-xs text-gray-500 mb-2">文件标题</div>
                      <input
                        value={draftTitle}
                        onChange={(event) => setDraftTitle(event.target.value)}
                        className="w-full rounded-xl border border-gray-800 bg-darker px-4 py-3 text-sm text-gray-100 outline-none focus:border-gold/50"
                        placeholder="输入可发布章节标题"
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <div className="text-xs text-gray-500">正文内容</div>
                        <div className="text-xs text-gray-600">{draftContent.length} 字符</div>
                      </div>
                      <textarea
                        value={draftContent}
                        onChange={(event) => setDraftContent(event.target.value)}
                        className="chapter-reading-editor min-h-[36rem] w-full rounded-xl border border-gray-800 bg-darker px-5 py-5 text-base leading-8 text-gray-100 outline-none focus:border-gold/50"
                        placeholder="# 第XXX章 标题"
                      />
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={handleSaveDraft}
                        disabled={!selectedNo || actionLoading}
                        className="chapter-primary-button inline-flex items-center gap-2 rounded-xl border border-gray-700 bg-darker px-4 py-2 text-sm text-gray-100 hover:bg-gray-800/70 disabled:opacity-50"
                      >
                        <Save size={16} />
                        保存正文
                      </button>
                      <button
                        type="button"
                        onClick={handleDiscardDraft}
                        className="chapter-secondary-button rounded-xl border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800/60"
                      >
                        放弃修改
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="bg-darker border border-gray-800 rounded-xl p-4">
                      <div className="text-xs text-gray-500 mb-2">当前标题</div>
                      <div className="chapter-reading-title text-base leading-7 text-gray-100">{draftTitle || '未命名章节'}</div>
                    </div>
                    <MarkdownBlock
                      content={compactedDraftContent}
                      height=""
                      className="chapter-reading-block px-7 py-7 text-gray-100"
                    />
                  </>
                )}
              </div>
            </Panel>

            <Panel title="上一章承接" icon={FileClock}>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">
                    第 {workflow?.recent_context?.chapter_no?.toString().padStart(3, '0') || '000'} 章时间线
                  </div>
                  <div className="text-sm text-gray-200 leading-6">
                    {workflow?.recent_context?.timeline_mark || '暂无记录'}
                  </div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">资产变化</div>
                  <div className="text-sm text-gray-200 leading-6">
                    {workflow?.recent_context?.key_assets_change || '暂无记录'}
                  </div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">上一章摘要</div>
                  <div className="text-sm text-gray-200 leading-6 whitespace-pre-wrap">
                    {workflow?.recent_context?.written_summary || '暂无记录'}
                  </div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">遗留钩子</div>
                  <div className="text-sm text-gray-200 leading-6 whitespace-pre-wrap">
                    {workflow?.recent_context?.next_hook || '暂无记录'}
                  </div>
                </div>
              </div>
            </Panel>

            <Panel
              title="正文实际出场角色"
              icon={Users}
              extra={
                <button
                  type="button"
                  onClick={handleRefreshCharacters}
                  disabled={!selectedNo || actionLoading}
                  className="chapter-secondary-button inline-flex items-center gap-2 rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-800/70 disabled:opacity-50"
                >
                  <RefreshCw size={14} />
                  按当前正文刷新
                </button>
              }
            >
              <div className="space-y-4">
                <CharacterModeHint mode={characterContext?.mode} />
                {characterContext?.actual_names?.length ? (
                  <div className="text-xs text-gray-400">
                    正文命中：{characterContext.actual_names.join('、')}
                  </div>
                ) : null}
                {characterContext?.requested_names?.length ? (
                  <div className="text-xs text-gray-400">
                    补申请：{characterContext.requested_names.join('、')}
                  </div>
                ) : null}
                {characterContext?.missing_names?.length ? (
                  <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-100">
                    未在角色库中找到：{characterContext.missing_names.join('、')}
                  </div>
                ) : null}
                {characterContext?.entries?.length ? (
                  characterContext.entries.map((entry) => (
                    <div key={entry.name} className="bg-darker border border-gray-800 rounded-xl p-4">
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <div className="text-base font-bold text-gray-100">{entry.name}</div>
                        <div className="text-xs text-gray-500">
                          {[entry.role_type, entry.occupation].filter(Boolean).join(' / ') || '角色'}
                        </div>
                      </div>
                      <div className="text-sm text-gray-300 leading-6">
                        <div><span className="text-gray-500">底色：</span>{entry.personality || '暂无记录'}</div>
                        <div><span className="text-gray-500">现状：</span>{entry.status || '暂无记录'}</div>
                        <div className="mt-2">
                          <span className="text-gray-500">近期经历：</span>
                          {entry.history?.length ? entry.history.join(' | ') : '暂无记录'}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">未识别到本章重点角色。</div>
                )}
              </div>
            </Panel>

            <Panel title="角色补充申请" icon={Users}>
              <div className="space-y-4">
                <div className="text-sm text-gray-400">
                  当正文里还没写到人名，但你准备让角色在本章出场时，可以先在这里补拉角色资料。
                </div>
                <textarea
                  value={requestedCharacters}
                  onChange={(event) => setRequestedCharacters(event.target.value)}
                  className="min-h-[6rem] w-full rounded-xl border border-gray-800 bg-darker px-4 py-3 text-sm leading-6 text-gray-100 outline-none focus:border-gold/50"
                  placeholder="输入角色名，多个名字可用顿号、逗号或空格分隔"
                />
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={handleRefreshCharacters}
                    disabled={!selectedNo || actionLoading}
                    className="inline-flex items-center gap-2 rounded-xl border border-gray-700 bg-darker px-4 py-2 text-sm text-gray-100 hover:bg-gray-800/70 disabled:opacity-50"
                  >
                    <Users size={16} />
                    提交补申请并刷新
                  </button>
                </div>
              </div>
            </Panel>
          </div>

          <div className="space-y-6">
            <Panel title="资产快照" icon={Wallet}>
              <div className="space-y-4">
                {workflow?.assets?.groups?.length ? (
                  workflow.assets.groups.map((group) => (
                    <div key={group.group} className="bg-darker border border-gray-800 rounded-xl p-4">
                      <div className="text-sm font-semibold text-gold mb-3">{group.label}</div>
                      <div className="space-y-2">
                        {group.items.map((item) => (
                          <div key={item.name} className="flex items-start justify-between gap-3 text-sm">
                            <div className="text-gray-300">{item.label}</div>
                            <div className="text-gray-100 text-right break-all">{item.display_value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">当前库中无可用的资产快照。</div>
                )}
              </div>
            </Panel>

            <Panel
              title="本章台账"
              icon={ShieldAlert}
              extra={
                <div className="flex items-center gap-2">
                  <DirtyBadge dirty={ledgerDirty} />
                  {!ledgerEditMode ? (
                    <button
                      type="button"
                      onClick={() => setLedgerEditMode(true)}
                      className="rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-800/70"
                    >
                      编辑台账
                    </button>
                  ) : null}
                </div>
              }
            >
              <div className="space-y-4">
                <div className="text-xs text-gray-500">
                  请保持 `## 章节更新` + `json` 代码块格式，闭环脚本会直接读取这里。
                </div>
                {ledgerEditMode ? (
                  <>
                    <textarea
                      value={ledgerContent}
                      onChange={(event) => setLedgerContent(event.target.value)}
                      className="min-h-[24rem] w-full rounded-xl border border-gray-800 bg-darker px-4 py-4 font-mono text-sm leading-6 text-gray-100 outline-none focus:border-gold/50"
                      placeholder="## 章节更新"
                    />
                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={handleSaveLedger}
                        disabled={!selectedNo || actionLoading}
                        className="inline-flex items-center gap-2 rounded-xl border border-gray-700 bg-darker px-4 py-2 text-sm text-gray-100 hover:bg-gray-800/70 disabled:opacity-50"
                      >
                        <Save size={16} />
                        保存台账
                      </button>
                      <button
                        type="button"
                        onClick={handleDiscardLedger}
                        className="rounded-xl border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800/60"
                      >
                        放弃修改
                      </button>
                    </div>
                  </>
                ) : (
                  <MarkdownBlock content={ledgerBaseline} height="max-h-[30rem]" />
                )}
              </div>
            </Panel>

            <Panel title="执行日志" icon={ShieldAlert}>
              <div className="space-y-4 text-sm text-gray-300">
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">写后摘要</div>
                  <div className="leading-6 whitespace-pre-wrap">{chapter?.written_summary || '暂无内容'}</div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">下一章钩子</div>
                  <div className="leading-6 whitespace-pre-wrap">{chapter?.next_hook || '暂无内容'}</div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">雷达文件位置</div>
                  <div className="break-all text-gray-400">{workflow?.radar?.path || '未生成'}</div>
                </div>
                <div className="bg-darker border border-gray-800 rounded-xl p-4">
                  <div className="text-xs text-gray-500 mb-2">最近执行日志</div>
                  <div className="leading-6 whitespace-pre-wrap text-gray-400">
                    {actionLog || '本次会话尚未执行写操作。'}
                  </div>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </main>
    </div>
  );
}
