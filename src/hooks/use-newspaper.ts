'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { format } from 'date-fns';
import type { 
  Language, 
  Newspaper, 
  Edition, 
  ProgressState 
} from '@/types';

interface UseNewspaperState {
  date: Date | null;
  language: string | null;
  newspaper: string | null;
  edition: string | null;
  languages: Language[];
  newspapers: Newspaper[];
  editions: Edition[];
  downloadUrl: string | null;
  downloadReady: boolean;
  error: string | null;
  progress: ProgressState | null;
  loading: {
    languages: boolean;
    newspapers: boolean;
    editions: boolean;
    download: boolean;
  };
}

export function useNewspaper() {
  const [state, setState] = useState<UseNewspaperState>({
    date: null,
    language: null,
    newspaper: null,
    edition: null,
    languages: [],
    newspapers: [],
    editions: [],
    downloadUrl: null,
    downloadReady: false,
    error: null,
    progress: null,
    loading: {
      languages: false,
      newspapers: false,
      editions: false,
      download: false,
    },
  });

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentRequestIdRef = useRef<string | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    currentRequestIdRef.current = null;
  }, []);

  const setDate = useCallback(async (date: Date | null) => {
    stopPolling();
    setState(prev => ({
      ...prev,
      date,
      language: null,
      newspaper: null,
      edition: null,
      languages: [],
      newspapers: [],
      editions: [],
      downloadUrl: null,
      downloadReady: false,
      error: null,
      progress: null,
      loading: { ...prev.loading, languages: !!date },
    }));

    if (!date) return;

    try {
      const dateStr = format(date, 'yyyyMMdd');
      const response = await fetch(`/api/data/${dateStr}`);
      const data = await response.json();

      if (data.success) {
        setState(prev => ({
          ...prev,
          languages: data.languages,
          loading: { ...prev.loading, languages: false },
        }));
      } else {
        setState(prev => ({
          ...prev,
          error: data.error || 'Failed to load languages',
          loading: { ...prev.loading, languages: false },
        }));
      }
    } catch {
      setState(prev => ({
        ...prev,
        error: 'Network error. Please try again.',
        loading: { ...prev.loading, languages: false },
      }));
    }
  }, [stopPolling]);

  const setLanguage = useCallback(async (languageId: string | null) => {
    stopPolling();
    setState(prev => ({
      ...prev,
      language: languageId,
      newspaper: null,
      edition: null,
      newspapers: [],
      editions: [],
      downloadUrl: null,
      downloadReady: false,
      error: null,
      progress: null,
      loading: { ...prev.loading, newspapers: !!languageId },
    }));

    if (!languageId || !state.date) return;

    try {
      const dateStr = format(state.date, 'yyyyMMdd');
      const response = await fetch(
        `/api/newspapers?date=${dateStr}&language=${languageId}`
      );
      const data = await response.json();

      if (data.success) {
        setState(prev => ({
          ...prev,
          newspapers: data.newspapers,
          loading: { ...prev.loading, newspapers: false },
        }));
      } else {
        setState(prev => ({
          ...prev,
          error: data.error || 'Failed to load newspapers',
          loading: { ...prev.loading, newspapers: false },
        }));
      }
    } catch {
      setState(prev => ({
        ...prev,
        error: 'Network error. Please try again.',
        loading: { ...prev.loading, newspapers: false },
      }));
    }
  }, [state.date, stopPolling]);

  const setNewspaper = useCallback(async (newspaperId: string | null) => {
    stopPolling();
    setState(prev => ({
      ...prev,
      newspaper: newspaperId,
      edition: null,
      editions: [],
      downloadUrl: null,
      downloadReady: false,
      error: null,
      progress: null,
      loading: { ...prev.loading, editions: !!newspaperId },
    }));

    if (!newspaperId || !state.date || !state.language) return;

    try {
      const dateStr = format(state.date, 'yyyyMMdd');
      const response = await fetch(
        `/api/editions?date=${dateStr}&language=${state.language}&newspaper=${newspaperId}`
      );
      const data = await response.json();

      if (data.success) {
        setState(prev => ({
          ...prev,
          editions: data.editions,
          loading: { ...prev.loading, editions: false },
        }));
      } else {
        setState(prev => ({
          ...prev,
          error: data.error || 'Failed to load editions',
          loading: { ...prev.loading, editions: false },
        }));
      }
    } catch {
      setState(prev => ({
        ...prev,
        error: 'Network error. Please try again.',
        loading: { ...prev.loading, editions: false },
      }));
    }
  }, [state.date, state.language, stopPolling]);

  const setEdition = useCallback((editionId: string | null) => {
    stopPolling();
    setState(prev => ({
      ...prev,
      edition: editionId,
      downloadUrl: null,
      downloadReady: false,
      error: null,
      progress: null,
    }));
  }, [stopPolling]);

  const pollProgress = useCallback(async (requestId: string) => {
    if (currentRequestIdRef.current !== requestId) return;

    try {
      const response = await fetch(`/api/pdf?jobId=${requestId}`);
      const data = await response.json();

      if (!data.success || currentRequestIdRef.current !== requestId) {
        return;
      }

      const progress = data.progress as ProgressState;
      
      setState(prev => ({
        ...prev,
        progress,
      }));

      if (progress.status === 'complete') {
        stopPolling();
        // Progress complete means PDF is ready on server
        // We need to fetch the final result
      } else if (progress.status === 'error') {
        stopPolling();
        setState(prev => ({
          ...prev,
          error: progress.message || 'Download failed',
          loading: { ...prev.loading, download: false },
        }));
      }
    } catch {
      // Polling error - continue trying
    }
  }, [stopPolling]);

  const startDownload = useCallback(async () => {
    if (!state.date || !state.language || !state.newspaper || !state.edition) {
      return;
    }

    stopPolling();
    
    const requestId = crypto.randomUUID();
    currentRequestIdRef.current = requestId;

    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, download: true },
      progress: {
        status: 'running',
        stage: 'validating',
        message: 'Initializing download...',
        logs: ['Starting download request'],
      },
      error: null,
      downloadUrl: null,
      downloadReady: false,
    }));

    // Start polling immediately
    pollIntervalRef.current = setInterval(() => {
      pollProgress(requestId);
    }, 500);

    try {
      const dateStr = format(state.date, 'yyyyMMdd');

      const response = await fetch('/api/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: dateStr,
          language: state.language,
          newspaper: state.newspaper,
          edition: state.edition,
          requestId,
        }),
      });

      const data = await response.json();

      // Stop polling since we have the result
      stopPolling();

      if (data.success && data.pdfUrl) {
        setState(prev => ({
          ...prev,
          downloadUrl: data.pdfUrl,
          downloadReady: true,
          progress: {
            status: 'complete',
            stage: 'complete',
            message: `Download ready (${data.pagesAdded || 0} pages)`,
            logs: prev.progress?.logs || [],
            current: data.pagesAdded || 0,
            total: data.pagesAdded || 0,
          },
          loading: { ...prev.loading, download: false },
        }));
      } else {
        setState(prev => ({
          ...prev,
          error: data.error || 'Failed to generate PDF',
          progress: {
            status: 'error',
            stage: 'error',
            message: data.error || 'Download failed',
            logs: prev.progress?.logs || [],
          },
          loading: { ...prev.loading, download: false },
        }));
      }
    } catch {
      stopPolling();
      setState(prev => ({
        ...prev,
        error: 'Network error. Please try again.',
        progress: null,
        loading: { ...prev.loading, download: false },
      }));
    }
  }, [state.date, state.language, state.newspaper, state.edition, stopPolling, pollProgress]);

  const triggerDownload = useCallback(() => {
    if (!state.downloadUrl) return;
    
    // Create filename from selections
    const dateStr = state.date ? format(state.date, 'yyyy-MM-dd') : 'newspaper';
    const filename = `${state.newspaper || 'newspaper'}_${dateStr}.pdf`;
    
    const link = document.createElement('a');
    link.href = state.downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [state.downloadUrl, state.date, state.newspaper]);

  const cancelDownload = useCallback(() => {
    stopPolling();
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, download: false },
      progress: null,
      error: null,
    }));
  }, [stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    setState({
      date: null,
      language: null,
      newspaper: null,
      edition: null,
      languages: [],
      newspapers: [],
      editions: [],
      downloadUrl: null,
      downloadReady: false,
      error: null,
      progress: null,
      loading: {
        languages: false,
        newspapers: false,
        editions: false,
        download: false,
      },
    });
  }, [stopPolling]);

  // Get selected items for display
  const selectedLanguage = state.languages.find(l => l.id === state.language);
  const selectedNewspaper = state.newspapers.find(n => n.id === state.newspaper);
  const selectedEdition = state.editions.find(e => e.id === state.edition);

  return {
    ...state,
    setDate,
    setLanguage,
    setNewspaper,
    setEdition,
    startDownload,
    triggerDownload,
    cancelDownload,
    reset,
    canStartDownload: !!(state.date && state.language && state.newspaper && state.edition && !state.loading.download),
    isAnyLoading: Object.values(state.loading).some(Boolean),
    selectedLanguage,
    selectedNewspaper,
    selectedEdition,
  };
}
