'use client';

import { useState, useCallback } from 'react';
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
  pdfUrl: string | null;
  error: string | null;
  progress: ProgressState | null;
  loading: {
    languages: boolean;
    newspapers: boolean;
    editions: boolean;
    pdf: boolean;
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
    pdfUrl: null,
    error: null,
    progress: null,
    loading: {
      languages: false,
      newspapers: false,
      editions: false,
      pdf: false,
    },
  });

  const setDate = useCallback(async (date: Date | null) => {
    setState(prev => ({
      ...prev,
      date,
      language: null,
      newspaper: null,
      edition: null,
      languages: [],
      newspapers: [],
      editions: [],
      pdfUrl: null,
      error: null,
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
  }, []);

  const setLanguage = useCallback(async (languageId: string | null) => {
    setState(prev => ({
      ...prev,
      language: languageId,
      newspaper: null,
      edition: null,
      newspapers: [],
      editions: [],
      pdfUrl: null,
      error: null,
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
  }, [state.date]);

  const setNewspaper = useCallback(async (newspaperId: string | null) => {
    setState(prev => ({
      ...prev,
      newspaper: newspaperId,
      edition: null,
      editions: [],
      pdfUrl: null,
      error: null,
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
  }, [state.date, state.language]);

  const setEdition = useCallback((editionId: string | null) => {
    setState(prev => ({
      ...prev,
      edition: editionId,
      pdfUrl: null,
      error: null,
    }));
  }, []);

  const fetchPdf = useCallback(async () => {
    if (!state.date || !state.language || !state.newspaper || !state.edition) {
      return;
    }

    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, pdf: true },
      progress: { stage: 'fetching', message: 'Fetching newspaper data...' },
      error: null,
      pdfUrl: null,
    }));

    try {
      const dateStr = format(state.date, 'yyyyMMdd');
      
      setState(prev => ({
        ...prev,
        progress: { stage: 'downloading', message: 'Downloading pages...' },
      }));

      const response = await fetch('/api/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: dateStr,
          language: state.language,
          newspaper: state.newspaper,
          edition: state.edition,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setState(prev => ({
          ...prev,
          pdfUrl: data.pdfUrl,
          progress: { stage: 'complete', message: 'PDF ready!' },
          loading: { ...prev.loading, pdf: false },
        }));
      } else {
        setState(prev => ({
          ...prev,
          error: data.error || 'Failed to generate PDF',
          progress: null,
          loading: { ...prev.loading, pdf: false },
        }));
      }
    } catch {
      setState(prev => ({
        ...prev,
        error: 'Network error. Please try again.',
        progress: null,
        loading: { ...prev.loading, pdf: false },
      }));
    }
  }, [state.date, state.language, state.newspaper, state.edition]);

  const reset = useCallback(() => {
    setState({
      date: null,
      language: null,
      newspaper: null,
      edition: null,
      languages: [],
      newspapers: [],
      editions: [],
      pdfUrl: null,
      error: null,
      progress: null,
      loading: {
        languages: false,
        newspapers: false,
        editions: false,
        pdf: false,
      },
    });
  }, []);

  return {
    ...state,
    setDate,
    setLanguage,
    setNewspaper,
    setEdition,
    fetchPdf,
    reset,
    canFetchPdf: !!(state.date && state.language && state.newspaper && state.edition),
    isAnyLoading: Object.values(state.loading).some(Boolean),
  };
}
